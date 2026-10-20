import contextlib
import io
import os
import tempfile
import subprocess
import unittest
from unittest import mock

from residual.cli import main
from residual.config import load_config
from residual.onboarding import (
    COMPOSE,
    FREELLMAPI_IMAGE,
    MANAGED_KEY_ENV,
    ManagedPaths,
    PROVIDERS,
    ensure_service_files,
    endpoint_ready,
    read_managed_key,
    setup,
    start_service,
    write_managed_config,
    write_unified_key,
)


class FreeLLMAPIOnboardingTests(unittest.TestCase):
    def test_managed_service_files_are_private_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            self.assertTrue(ensure_service_files(paths))
            first_key = paths.service_env.read_text()
            self.assertEqual(paths.compose.read_text(), COMPOSE)
            self.assertIn("HOST_BIND=127.0.0.1", first_key)
            self.assertIn("ENCRYPTION_KEY=", first_key)
            self.assertFalse(ensure_service_files(paths))
            self.assertEqual(paths.service_env.read_text(), first_key)
            if os.name != "nt":
                self.assertEqual(paths.service_env.stat().st_mode & 0o077, 0)

    def test_managed_image_is_immutable_digest_pin(self):
        self.assertIn("@sha256:", FREELLMAPI_IMAGE)
        self.assertNotIn(":latest", FREELLMAPI_IMAGE)
        self.assertIn(FREELLMAPI_IMAGE, COMPOSE)

    def test_generated_config_uses_private_secret_file_not_inline_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            write_unified_key(paths, "freellmapi-test-secret")
            write_managed_config(paths)
            text = paths.config.read_text()
            self.assertNotIn("freellmapi-test-secret", text)
            self.assertIn('api_key_env = "RESIDUAL_FREELLMAPI_KEY"', text)
            self.assertIn('placement = "remote"', text)
            old = os.environ.pop(MANAGED_KEY_ENV, None)
            try:
                config = load_config(paths.config)
                self.assertEqual(os.environ[MANAGED_KEY_ENV], "freellmapi-test-secret")
                self.assertEqual(config["expert"]["kind"], "openai_compatible")
                self.assertEqual(config["expert"]["placement"], "remote")
                self.assertNotIn("secrets", config)
            finally:
                os.environ.pop(MANAGED_KEY_ENV, None)
                if old is not None:
                    os.environ[MANAGED_KEY_ENV] = old

    def test_environment_wins_over_managed_secret_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            write_unified_key(paths, "file-value")
            write_managed_config(paths)
            old = os.environ.get(MANAGED_KEY_ENV)
            os.environ[MANAGED_KEY_ENV] = "environment-value"
            try:
                load_config(paths.config)
                self.assertEqual(os.environ[MANAGED_KEY_ENV], "environment-value")
            finally:
                if old is None:
                    os.environ.pop(MANAGED_KEY_ENV, None)
                else:
                    os.environ[MANAGED_KEY_ENV] = old

    def test_noninteractive_setup_can_prepare_without_docker(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            paths = ManagedPaths.from_value(tmp)
            code = setup(paths, provider_id="groq", non_interactive=True,
                         skip_start=True, skip_smoke=True)
            self.assertEqual(code, 0)
            self.assertTrue(paths.config.exists())
            self.assertTrue(paths.compose.exists())
            self.assertIsNone(read_managed_key(paths))

    def test_model_backslash_is_serialized_without_changing_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            write_unified_key(paths, "key")
            write_managed_config(paths, model="vendor\\name")
            with mock.patch.dict(os.environ):
                self.assertEqual(load_config(paths.config)["expert"]["model"], "vendor\\name")

    def test_authenticated_probe_disables_redirects(self):
        from residual.providers import NoRedirect, ProviderError
        with mock.patch("residual.onboarding.urllib.request.build_opener") as build:
            build.return_value.open.side_effect = ProviderError("http_redirect_refused")
            self.assertFalse(endpoint_ready("private-key"))
        self.assertTrue(any(isinstance(handler, NoRedirect) for handler in build.call_args.args))

    def test_provider_manifest_has_actionable_links(self):
        self.assertEqual(set(PROVIDERS), {"groq", "google", "cerebras", "mistral", "openrouter"})
        for provider in PROVIDERS.values():
            self.assertTrue(provider.signup_url.startswith("https://"))
            self.assertTrue(provider.platform)

    def test_cli_providers_list_is_network_free(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["providers", "list"]), 0)
        self.assertIn("Groq", output.getvalue())
        self.assertIn("OpenRouter", output.getvalue())

    @mock.patch("residual.onboarding.ensure_service_files")
    @mock.patch("residual.onboarding.compose_available", return_value=True)
    @mock.patch("residual.onboarding.docker_available", return_value=True)
    @mock.patch("residual.onboarding.wait_for_http", return_value=False)
    @mock.patch("residual.onboarding._run")
    def test_bootstrap_readiness_failure_still_scrubs_secret(
            self, run, _http, _docker, _compose, _files):
        run.side_effect = [
            mock.Mock(returncode=0),  # bootstrap compose up
            mock.Mock(returncode=0),  # scrub force-recreate
        ]
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            ok, detail = start_service(paths, {"keys": [{"key": "secret"}]})
        self.assertFalse(ok)
        self.assertIn("credential scrubbed", detail)
        self.assertEqual(run.call_count, 2)
        scrub_env = run.call_args_list[1].kwargs["env"]
        self.assertEqual(scrub_env["FREEAPI_CONFIG_JSON"], "")

    @mock.patch("residual.onboarding.ensure_service_files")
    @mock.patch("residual.onboarding.compose_available", return_value=True)
    @mock.patch("residual.onboarding.docker_available", return_value=True)
    @mock.patch("residual.onboarding.wait_for_http", return_value=True)
    @mock.patch("residual.onboarding._run")
    def test_bootstrap_scrub_failure_stops_service(
            self, run, _http, _docker, _compose, _files):
        run.side_effect = [
            mock.Mock(returncode=0),  # bootstrap compose up
            mock.Mock(returncode=1),  # scrub force-recreate
            mock.Mock(returncode=0),  # fail-closed compose down
        ]
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            ok, detail = start_service(paths, {"keys": [{"key": "secret"}]})
        self.assertFalse(ok)
        self.assertIn("managed service stopped", detail)
        self.assertEqual(run.call_count, 3)
        self.assertIn("down", run.call_args_list[2].args[0])
        self.assertEqual(run.call_args_list[2].kwargs["env"]["FREEAPI_CONFIG_JSON"], "")

    def test_secret_write_does_not_follow_predictable_temporary_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ManagedPaths.from_value(tmp)
            victim = paths.home / "victim"
            victim.write_text("unchanged")
            paths.secrets_env.with_name("secrets.env.tmp").symlink_to(victim)
            write_unified_key(paths, "private-key")
            self.assertEqual(victim.read_text(), "unchanged")
            self.assertEqual(read_managed_key(paths), "private-key")

    @mock.patch("residual.onboarding.ensure_service_files")
    @mock.patch("residual.onboarding.compose_available", return_value=True)
    @mock.patch("residual.onboarding.docker_available", return_value=True)
    @mock.patch("residual.onboarding._run")
    def test_bootstrap_timeout_still_scrubs(self, run, _docker, _compose, _files):
        run.side_effect = [subprocess.TimeoutExpired("docker", 180), mock.Mock(returncode=0)]
        with tempfile.TemporaryDirectory() as tmp:
            ok, detail = start_service(ManagedPaths.from_value(tmp), {"keys": [{"key": "secret"}]})
        self.assertFalse(ok)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].kwargs["env"]["FREEAPI_CONFIG_JSON"], "")

    @mock.patch("residual.onboarding.ensure_service_files")
    @mock.patch("residual.onboarding.compose_available", return_value=True)
    @mock.patch("residual.onboarding.docker_available", return_value=True)
    @mock.patch("residual.onboarding.wait_for_http", return_value=True)
    @mock.patch("residual.onboarding._run")
    def test_cleanup_failure_is_not_reported_as_stopped(self, run, _http, _docker, _compose, _files):
        run.side_effect = [mock.Mock(returncode=0), subprocess.TimeoutExpired("docker", 180), mock.Mock(returncode=1)]
        with tempfile.TemporaryDirectory() as tmp:
            ok, detail = start_service(ManagedPaths.from_value(tmp), {"keys": [{"key": "secret"}]})
        self.assertFalse(ok)
        self.assertIn("cleanup unconfirmed", detail)
        self.assertNotIn("service stopped", detail)

    @mock.patch("residual.onboarding.wait_for_http", return_value=False)
    @mock.patch("residual.onboarding.compose_available", return_value=False)
    @mock.patch("residual.onboarding.docker_available", return_value=False)
    def test_doctor_json_reports_missing_runtime_without_crashing(self, _docker, _compose, _http):
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["doctor", "--home", tmp, "--json"])
            self.assertEqual(code, 1)
            self.assertIn('"name": "docker"', output.getvalue())
            self.assertIn('"status": "fail"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
