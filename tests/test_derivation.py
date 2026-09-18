from __future__ import annotations

import unittest

from residual.core import ContractError
from residual.derivation import (
    Author, DerivationEdge, DerivationGraph, DerivationNode,
    EdgeType, NodeType, Validity,
)


def node(kind, author, **payload):
    return DerivationNode(kind, author, payload)


def edge(kind, source, target, **predicate):
    return DerivationEdge(kind, source.node_id, target.node_id, predicate)


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

    def test_dg003_bad_framing_blocks_admission_even_with_valid_attestation(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,metric="latency_mean_ms",value=100)
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="p99 tail latency is too high")
        invariant=node(NodeType.INVARIANT_VERDICT,Author.HOST,verdict="fail",rule="tail claim requires tail aggregation")
        review=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="invalid",reason="mean cannot test p99")
        env=node(NodeType.ENVIRONMENT_VERDICT,Author.HOST,verdict="pass")
        human=node(NodeType.HUMAN_DECISION,Author.HUMAN,decision="cosign")
        spec=node(
            NodeType.IMPROVEMENT_SPEC,Author.PLANNER,
            intent="reduce tail latency",mechanism="bounded synthetic change",
            predicted_effects={"latency_p99_ms":"decrease"},
            verification_plan={"metric":"latency_mean_ms"},
            preservation_criteria={"correctness":"no regression"},
            rollback_plan={"action":"revert"},
        )
        edges=[
            edge(EdgeType.SUPPORTED_BY,finding,evidence,required=True),
            edge(EdgeType.SUPPORTED_BY,spec,finding,required=True),
            edge(EdgeType.PRESERVES,spec,invariant,required=True),
            edge(EdgeType.REVIEWED_BY,spec,review,required=True),
            edge(EdgeType.QUALIFIED_UNDER,spec,env,required=True),
            edge(EdgeType.AUTHORIZED_BY,spec,human,required=True),
        ]
        g=DerivationGraph([evidence,finding,invariant,review,env,human,spec],edges)
        ok,findings=g.improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertTrue(any("review" in x or "invariant" in x for x in findings))

    def test_positive_admission_requires_complete_valid_subgraph(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,metric="latency_p99_ms",value=240)
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="p99 tail latency is elevated")
        invariant=node(NodeType.INVARIANT_VERDICT,Author.HOST,verdict="pass")
        review=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="valid")
        env=node(NodeType.ENVIRONMENT_VERDICT,Author.HOST,verdict="pass")
        human=node(NodeType.HUMAN_DECISION,Author.HUMAN,decision="cosign")
        spec=node(
            NodeType.IMPROVEMENT_SPEC,Author.PLANNER,
            intent="reduce p99 tail latency",mechanism="bounded synthetic change",
            predicted_effects={"latency_p99_ms":"decrease"},
            verification_plan={"metric":"latency_p99_ms","operator":"<"},
            preservation_criteria={"correctness":"no regression"},
            rollback_plan={"action":"revert"},
        )
        edges=[
            edge(EdgeType.SUPPORTED_BY,finding,evidence,required=True),
            edge(EdgeType.SUPPORTED_BY,spec,finding,required=True),
            edge(EdgeType.PRESERVES,spec,invariant,required=True),
            edge(EdgeType.REVIEWED_BY,spec,review,required=True),
            edge(EdgeType.QUALIFIED_UNDER,spec,env,required=True),
            edge(EdgeType.AUTHORIZED_BY,spec,human,required=True),
        ]
        g=DerivationGraph([evidence,finding,invariant,review,env,human,spec],edges)
        ok,findings=g.improvement_admissible(spec.node_id)
        self.assertTrue(ok,findings)

    def test_missing_human_cosign_blocks_positive_admission(self):
        evidence=node(NodeType.EVIDENCE_FACT,Author.HOST,metric="latency_p99_ms",value=240)
        finding=node(NodeType.FINDING,Author.SCIENTIST,claim="p99 elevated")
        invariant=node(NodeType.INVARIANT_VERDICT,Author.HOST,verdict="pass")
        review=node(NodeType.SEMANTIC_REVIEW,Author.REVIEWER,verdict="valid")
        env=node(NodeType.ENVIRONMENT_VERDICT,Author.HOST,verdict="pass")
        spec=node(
            NodeType.IMPROVEMENT_SPEC,Author.PLANNER,
            intent="reduce p99",mechanism="bounded change",
            predicted_effects={"latency_p99_ms":"decrease"},
            verification_plan={"metric":"latency_p99_ms"},
            preservation_criteria={"correctness":"stable"},
            rollback_plan={"action":"revert"},
        )
        edges=[
            edge(EdgeType.SUPPORTED_BY,finding,evidence),
            edge(EdgeType.SUPPORTED_BY,spec,finding),
            edge(EdgeType.PRESERVES,spec,invariant),
            edge(EdgeType.REVIEWED_BY,spec,review),
            edge(EdgeType.QUALIFIED_UNDER,spec,env),
        ]
        g=DerivationGraph([evidence,finding,invariant,review,env,spec],edges)
        ok,findings=g.improvement_admissible(spec.node_id)
        self.assertFalse(ok)
        self.assertIn("missing valid authorized_by justification",findings)


if __name__=="__main__":
    unittest.main()
