from __future__ import annotations

import unittest

from residual.core import ContractError
from residual.derivation import (
    Author, DerivationEdge, DerivationGraph, DerivationNode,
    EdgeType, NodeType, Validity,
)


CHALLENGEABLE={
    NodeType.QUESTION,NodeType.FINDING,NodeType.METRIC_DECISION,
    NodeType.SEMANTIC_REVIEW,NodeType.IMPROVEMENT_SPEC,
}


def node(kind, author, **payload):
    return DerivationNode(
        kind,author,payload,
        challenge_policy_id="m6-semantic-v1" if kind in CHALLENGEABLE else None,
    )


def edge(kind, source, target, **predicate):
    return DerivationEdge(kind, source.node_id, target.node_id, predicate)


def policy_node():
    return node(
        NodeType.CHALLENGE_POLICY,Author.HOST,
        policy_id="m6-semantic-v1",
        eligible_challenger_roles=["reviewer","human"],
        allowed_grounds=["semantic","evidence","framing","authorization"],
        resolution_authority_roles=["human"],
        filing_window_events=None,
        allow_withdrawal=True,
        revision="1",
    )


def challenge_node(target, challenge_id, *, role="reviewer", ground="semantic", filed_event=1, reason="challenge"):
    return node(
        NodeType.CHALLENGE,
        Author.REVIEWER if role=="reviewer" else Author.HUMAN,
        challenge_id=challenge_id,
        policy_id=target.challenge_policy_id,
        challenger_role=role,
        ground=ground,
        filed_event=filed_event,
        reason=reason,
    )


def admissible_fixture(include_human=True):
    evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,metric="latency_p99_ms",value=240)
    finding=node(NodeType.FINDING,Author.SCIENTIST,claim="p99 tail latency is elevated")
    metric=node(
        NodeType.METRIC_DECISION,Author.PLANNER,
        selector={"core_quantity":"latency","aggregation":"p99"},
        rationale="p99 directly measures the stated tail-latency behavior under test",
    )
    resolution=node(NodeType.METRIC_RESOLUTION,Author.HOST,metric_id="latency_p99_ms")
    metric_review=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="valid",rationale="p99 is the appropriate lens")
    invariant=node(NodeType.INVARIANT_VERDICT,Author.HOST,verdict="pass")
    review=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="valid",rationale="spec is falsifiable")
    env=node(NodeType.ENVIRONMENT_VERDICT,Author.HOST,verdict="pass")
    spec=node(
        NodeType.IMPROVEMENT_SPEC,Author.PLANNER,
        intent="reduce p99 tail latency",mechanism="bounded synthetic change",
        predicted_effects={"latency_p99_ms":"decrease"},
        verification_plan={"metric":"latency_p99_ms","operator":"<"},
        preservation_criteria={"correctness":"no regression"},
        rollback_plan={"action":"revert"},
    )
    policy=policy_node()
    author_env=node(
        NodeType.ENVIRONMENT_CONTEXT,Author.HOST,
        runner="github-actions",queue_latency_s=120,
        model_runtime="qwen2.5:7b",status="observed",
    )
    nodes=[evidence,finding,metric,resolution,metric_review,invariant,review,env,spec,policy,author_env]
    edges=[
        edge(EdgeType.GOVERNED_BY,finding,policy),
        edge(EdgeType.GOVERNED_BY,metric,policy),
        edge(EdgeType.GOVERNED_BY,metric_review,policy),
        edge(EdgeType.GOVERNED_BY,review,policy),
        edge(EdgeType.GOVERNED_BY,spec,policy),
        edge(EdgeType.AUTHORED_UNDER,finding,author_env),
        edge(EdgeType.AUTHORED_UNDER,metric,author_env),
        edge(EdgeType.AUTHORED_UNDER,metric_review,author_env),
        edge(EdgeType.AUTHORED_UNDER,review,author_env),
        edge(EdgeType.AUTHORED_UNDER,spec,author_env),
        edge(EdgeType.SUPPORTED_BY,finding,evidence,required=True),
        edge(EdgeType.RESOLVES_TO,metric,resolution,required=True),
        edge(EdgeType.REVIEWED_BY,metric,metric_review,required=True),
        edge(EdgeType.SUPPORTED_BY,spec,finding,required=True),
        edge(EdgeType.MEASURED_BY,spec,metric,required=True),
        edge(EdgeType.PRESERVES,spec,invariant,required=True),
        edge(EdgeType.REVIEWED_BY,spec,review,required=True),
        edge(EdgeType.QUALIFIED_UNDER,spec,env,required=True),
    ]
    if include_human:
        human=node(NodeType.HUMAN_DECISION,Author.HUMAN,decision="cosign")
        nodes.append(human)
        edges.append(edge(EdgeType.AUTHORIZED_BY,spec,human,required=True))
    return nodes,edges,spec,metric


class DerivationGraphTests(unittest.TestCase):
    def test_dg001_root_is_insertion_order_independent(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,metric="latency_p99_ms",value=240)
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="tail latency is elevated")
        support=edge(EdgeType.SUPPORTED_BY,finding,evidence,required=True)
        a=DerivationGraph([evidence,finding],[support])
        b=DerivationGraph([finding,evidence],[support])
        self.assertEqual(a.graph_root,b.graph_root)

    def test_dg001_one_byte_semantic_change_changes_root(self):
        e1=node(NodeType.EVIDENCE_FACT,Author.HOST,value="abc")
        e2=node(NodeType.EVIDENCE_FACT,Author.HOST,value="abd")
        self.assertNotEqual(DerivationGraph([e1],[]).graph_root,DerivationGraph([e2],[]).graph_root)

    def test_graph_rejects_unknown_node_edge(self):
        a=node(NodeType.FINDING,Author.SCIENTIST,claim="x")
        b=node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)
        e=edge(EdgeType.SUPPORTED_BY,a,b,required=True)
        with self.assertRaisesRegex(ContractError,"unknown node"):
            DerivationGraph([a],[e])

    def test_graph_rejects_invalid_edge_type_pair(self):
        a=node(NodeType.HUMAN_DECISION,Author.HUMAN,decision="cosign")
        b=node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)
        e=edge(EdgeType.SUPPORTED_BY,a,b,required=True)
        with self.assertRaisesRegex(ContractError,"invalid for"):
            DerivationGraph([a,b],[e])

    def test_graph_rejects_dependency_cycle(self):
        a=node(NodeType.METRIC_RESOLUTION,Author.HOST,name="a")
        b=node(NodeType.METRIC_RESOLUTION,Author.HOST,name="b")
        e1=edge(EdgeType.REFINES,a,b,strict=True)
        e2=edge(EdgeType.REFINES,b,a,strict=True)
        with self.assertRaisesRegex(ContractError,"cycle"):
            DerivationGraph([a,b],[e1,e2])

    def test_dg002_challenge_localizes_invalidation(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)
        finding_a=node(NodeType.FINDING,Author.SCIENTIST,claim="A")
        finding_b=node(NodeType.FINDING,Author.SCIENTIST,claim="B")
        review_a=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="valid")
        policy=policy_node()\n        challenge=challenge_node(review_a,"ch-dg002",reason="A is framed badly")
        edges=[
            edge(EdgeType.SUPPORTED_BY,finding_a,evidence,required=True),
            edge(EdgeType.SUPPORTED_BY,finding_b,evidence,required=True),
            edge(EdgeType.REVIEWED_BY,finding_a,review_a,required=True),
            edge(EdgeType.CHALLENGES,challenge,review_a,reason="semantic"),
        ]
        edges.append(edge(EdgeType.GOVERNED_BY,review_a,policy))\n        g=DerivationGraph([evidence,finding_a,finding_b,review_a,challenge,policy],edges)
        states=g.validity()
        self.assertEqual(states[review_a.node_id],Validity.CHALLENGED)
        self.assertEqual(states[finding_a.node_id],Validity.CHALLENGED)
        self.assertEqual(states[finding_b.node_id],Validity.VALID)
        self.assertEqual(states[evidence.node_id],Validity.VALID)

    def test_challenge_is_append_only_and_changes_graph_root(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="A")
        support=edge(EdgeType.SUPPORTED_BY,finding,evidence,required=True)
        before=DerivationGraph([evidence,finding],[support])
        policy=policy_node()\n        challenge=challenge_node(finding,"ch-append",reason="challenge")
        challenge_edge=edge(EdgeType.CHALLENGES,challenge,finding,reason="new evidence")
        after=DerivationGraph([evidence,finding,challenge,policy],[support,challenge_edge,edge(EdgeType.GOVERNED_BY,finding,policy)])
        self.assertIn(finding.node_id,after.nodes)
        self.assertNotEqual(before.graph_root,after.graph_root)

    def test_dg003_bad_framing_blocks_admission(self):
        nodes,edges,spec,metric=admissible_fixture()
        # Replace the metric decision with a mean-only lens while keeping the
        # tail claim, then add explicit semantic failures.
        mean_metric=node(
            NodeType.METRIC_DECISION,Author.PLANNER,
            selector={"core_quantity":"latency","aggregation":"mean"},
            rationale="mean latency is easy to collect but does not directly test the p99 claim",
        )
        resolution=node(NodeType.METRIC_RESOLUTION,Author.HOST,metric_id="latency_mean_ms")
        bad_review=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="invalid",reason="mean cannot test p99")
        nodes=[n for n in nodes if n.node_id not in {metric.node_id}]
        edges=[e for e in edges if e.source!=metric.node_id and e.target!=metric.node_id and e.edge_type!=EdgeType.MEASURED_BY]
        nodes.extend([mean_metric,resolution,bad_review])
        edges.extend([
            edge(EdgeType.RESOLVES_TO,mean_metric,resolution),
            edge(EdgeType.REVIEWED_BY,mean_metric,bad_review),
            edge(EdgeType.MEASURED_BY,spec,mean_metric),
        ])
        g=DerivationGraph(nodes,edges)
        ok,findings=g.improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertTrue(any("measured_by" in x or "review" in x for x in findings))

    def test_positive_admission_requires_complete_valid_subgraph(self):
        nodes,edges,spec,_=admissible_fixture()
        ok,findings=DerivationGraph(nodes,edges).improvement_admissible(spec.node_id)
        self.assertTrue(ok,findings)

    def test_missing_human_cosign_blocks_positive_admission(self):
        nodes,edges,spec,_=admissible_fixture(include_human=False)
        ok,findings=DerivationGraph(nodes,edges).improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertIn("missing valid authorized_by justification",findings)

    def test_ch001_semantic_nodes_require_challenge_policy(self):
        with self.assertRaisesRegex(ContractError,"requires challenge_policy_id"):
            DerivationNode(NodeType.FINDING,Author.SCIENTIST,{"claim":"x"})
        with self.assertRaisesRegex(ContractError,"cannot disable challengeability"):
            DerivationNode(
                NodeType.FINDING,Author.SCIENTIST,
                {"claim":"x","challengeable":False},
                challenge_policy_id="m6-semantic-v1",
            )

    def test_ca001_open_challenge_blocks_complete_spec(self):
        nodes,edges,spec,metric=admissible_fixture()
        challenge=challenge_node(metric,"ch-ca001",reason="metric rationale disputed")
        nodes.append(challenge)
        edges.append(edge(EdgeType.CHALLENGES,challenge,metric,reason="wrong lens"))
        g=DerivationGraph(nodes,edges)
        ok,findings=g.improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertTrue(any("challenge" in x or "measured_by" in x for x in findings))

    def test_ca001_superseded_challenge_stops_active_invalidation(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="A")
        policy=policy_node()\n        challenge=challenge_node(finding,"ch-resolve",reason="open objection")
        resolution=node(NodeType.SUPERSESSION,Author.HOST,reason="challenge resolved under policy")
        edges=[
            edge(EdgeType.SUPPORTED_BY,finding,evidence),
            edge(EdgeType.CHALLENGES,challenge,finding,reason="semantic"),
            edge(EdgeType.SUPERSEDES,resolution,challenge,policy="m6-semantic-v1"),
        ]
        edges.append(edge(EdgeType.GOVERNED_BY,finding,policy))\n        g=DerivationGraph([evidence,finding,challenge,resolution,policy],edges)
        self.assertEqual(g.validity()[challenge.node_id],Validity.SUPERSEDED)
        self.assertEqual(g.validity()[finding.node_id],Validity.VALID)

    def test_hr001_persistent_handle_resolution_is_graph_bound(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,value={"metric":"p99","value":240})
        resolution=node(NodeType.CAPABILITY_RESOLUTION,Author.HOST,invocation_id="inv-a",handle="ev_3")
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="tail elevated",evidence_handles=["ev_3"])
        edges=[
            edge(EdgeType.CITES_HANDLE,finding,resolution,handle="ev_3",invocation_id="inv-a"),
            edge(EdgeType.RESOLVES_TO,resolution,evidence,host_attested=True),
        ]
        g=DerivationGraph([evidence,resolution,finding],edges)
        replay=DerivationGraph(list(g.nodes.values()),list(g.edges.values()))
        self.assertEqual(g.graph_root,replay.graph_root)
        resolved=replay.resolve_historical_handle(
            author_node_id=finding.node_id,invocation_id="inv-a",handle="ev_3"
        )
        self.assertEqual(resolved.node_id,evidence.node_id)
        with self.assertRaisesRegex(ContractError,"missing or ambiguous"):
            replay.resolve_historical_handle(
                author_node_id=finding.node_id,invocation_id="inv-b",handle="ev_3"
            )

    def test_au001_challenged_authorization_invalidates_execution(self):
        human=node(NodeType.HUMAN_DECISION,Author.HUMAN,decision="cosign")
        spec=node(NodeType.IMPROVEMENT_SPEC,Author.PLANNER,intent="x",mechanism="y",predicted_effects={},verification_plan={},preservation_criteria={},rollback_plan={})
        action=node(NodeType.EXECUTION_ACTION,Author.HOST,action="stage candidate")
        revoke=node(NodeType.REVOCATION,Author.HUMAN,reason="authorization revoked")
        edges=[
            edge(EdgeType.AUTHORIZES,human,action,scope="tier2"),
            edge(EdgeType.IMPLEMENTS,action,spec),
            edge(EdgeType.REVOKES,revoke,human,reason="revoked"),
        ]
        g=DerivationGraph([human,spec,action,revoke],edges)
        self.assertEqual(g.validity()[action.node_id],Validity.AUTHORIZATION_REVOKED)

    def test_temporal_admission_record_preserves_then_current_challenge_changes_state(self):
        nodes,edges,spec,metric=admissible_fixture()
        before=DerivationGraph(nodes,edges)
        decision=before.admission_decision_node(spec.node_id,event_index=50)
        self.assertEqual(decision.payload["verdict"],"admitted")
        self.assertEqual(decision.payload["evaluated_graph_root"],before.graph_root)

        challenge=challenge_node(metric,"ch-temporal",filed_event=51,reason="later semantic objection")
        after=DerivationGraph(
            nodes+[challenge,decision],
            edges+[
                edge(EdgeType.CHALLENGES,challenge,metric,reason="later evidence"),
                edge(EdgeType.ADMITTED_FROM,decision,spec,evaluated_event=50),
            ],
        )
        ok,_=after.improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertEqual(decision.payload["verdict"],"admitted")

    def test_explicit_revocation_marks_future_execution_authorization_revoked(self):
        human=node(NodeType.HUMAN_DECISION,Author.HUMAN,decision="cosign")
        spec=node(NodeType.IMPROVEMENT_SPEC,Author.PLANNER,intent="x",mechanism="y",predicted_effects={},verification_plan={},preservation_criteria={},rollback_plan={})
        action=node(NodeType.EXECUTION_ACTION,Author.HOST,action="stage")
        revoke=node(NodeType.REVOCATION,Author.HUMAN,reason="withdraw future authority")
        g=DerivationGraph(
            [human,spec,action,revoke],
            [
                edge(EdgeType.AUTHORIZES,human,action,scope="tier2"),
                edge(EdgeType.IMPLEMENTS,action,spec),
                edge(EdgeType.REVOKES,revoke,human,reason="revoked"),
            ],
        )
        self.assertEqual(g.validity()[human.node_id],Validity.AUTHORIZATION_REVOKED)
        self.assertEqual(g.validity()[action.node_id],Validity.AUTHORIZATION_REVOKED)

    def test_execution_binding_is_explicit_and_challengeable(self):
        policy=policy_node()
        snapshot=node(NodeType.DERIVATION_SNAPSHOT,Author.HOST,graph_root="a"*64)
        env=node(NodeType.ENVIRONMENT_CONTEXT,Author.HOST,observed_environment_hash="b"*64)
        base=DerivationGraph([policy,snapshot,env],[])
        binding=base.execution_binding_node(
            snapshot_node_id=snapshot.node_id,
            environment_context_id=env.node_id,
            input_artifact_commitments={"repo":"c"*64},
            challenge_policy_id="m6-semantic-v1",
        )
        challenge=challenge_node(binding,"ch-binding",reason="undeclared input artifact")
        g=DerivationGraph(
            [policy,snapshot,env,binding,challenge],
            [
                edge(EdgeType.GOVERNED_BY,binding,policy),
                edge(EdgeType.EXECUTES,binding,snapshot),
                edge(EdgeType.UNDER_ENVIRONMENT,binding,env),
                edge(EdgeType.CHALLENGES,challenge,binding,reason="binding mismatch"),
            ],
        )
        self.assertEqual(g.validity()[binding.node_id],Validity.CHALLENGED)

    def test_relative_quiescence_requires_exhausted_policy_and_zero_admissible_specs(self):
        g=DerivationGraph([node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)],[])
        cert=g.quiescence_certificate_node(
            scope="m6-current-roadmap",
            evidence_root="a"*64,
            metric_theory_root="b"*64,
            search_policy_revision="scientist-search-v1",
            search_budget={"max_candidates":100},
            evaluated_candidates=100,
            admissible_candidates=0,
            exhaustive_under_policy=True,
        )
        self.assertEqual(cert.payload["claim"],"relative_quiescence_not_global_optimum")
        with self.assertRaisesRegex(ContractError,"quiescence requires"):
            g.quiescence_certificate_node(
                scope="m6-current-roadmap",evidence_root="a"*64,
                metric_theory_root="b"*64,search_policy_revision="v1",
                search_budget={"max_candidates":100},evaluated_candidates=10,
                admissible_candidates=0,exhaustive_under_policy=False,
            )

    def test_env002_semantic_root_stable_execution_root_environment_bound(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,value=1)
        g=DerivationGraph([evidence],[])
        semantic_root=g.graph_root
        a=g.execution_root(
            environment_contract_hash="1"*64,
            observed_environment_hash="2"*64,
            input_artifact_commitments={"repo":"3"*64},
        )
        b=g.execution_root(
            environment_contract_hash="1"*64,
            observed_environment_hash="4"*64,
            input_artifact_commitments={"repo":"3"*64},
        )
        self.assertEqual(semantic_root,g.graph_root)
        self.assertNotEqual(a,b)


if __name__=="__main__":
    unittest.main()
