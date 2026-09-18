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
    nodes=[evidence,finding,metric,resolution,metric_review,invariant,review,env,spec]
    edges=[
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
        challenge=node(NodeType.CHALLENGE,Author.REVIEWER,reason="A is framed badly")
        edges=[
            edge(EdgeType.SUPPORTED_BY,finding_a,evidence,required=True),
            edge(EdgeType.SUPPORTED_BY,finding_b,evidence,required=True),
            edge(EdgeType.REVIEWED_BY,finding_a,review_a,required=True),
            edge(EdgeType.CHALLENGES,challenge,review_a,reason="semantic"),
        ]
        g=DerivationGraph([evidence,finding_a,finding_b,review_a,challenge],edges)
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
        challenge=node(NodeType.CHALLENGE,Author.REVIEWER,reason="challenge")
        challenge_edge=edge(EdgeType.CHALLENGES,challenge,finding,reason="new evidence")
        after=DerivationGraph([evidence,finding,challenge],[support,challenge_edge])
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
        challenge=node(NodeType.CHALLENGE,Author.REVIEWER,reason="metric rationale disputed")
        nodes.append(challenge)
        edges.append(edge(EdgeType.CHALLENGES,challenge,metric,reason="wrong lens"))
        g=DerivationGraph(nodes,edges)
        ok,findings=g.improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertTrue(any("challenge" in x or "measured_by" in x for x in findings))

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
        challenge=node(NodeType.CHALLENGE,Author.HUMAN,reason="authorization revoked")
        edges=[
            edge(EdgeType.AUTHORIZES,human,action,scope="tier2"),
            edge(EdgeType.IMPLEMENTS,action,spec),
            edge(EdgeType.CHALLENGES,challenge,human,reason="revoked"),
        ]
        g=DerivationGraph([human,spec,action,challenge],edges)
        self.assertEqual(g.validity()[action.node_id],Validity.CHALLENGED)

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
