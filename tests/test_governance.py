"""治理效率衰减模型测试（文档 §3.2 标定 + 边界）。"""

from __future__ import annotations

import math

import pytest

from backend.engine.governance import governance_efficiency


class TestGovernanceCalibration:
    """文档给出的三组标定数值。"""

    def test_early_civilization(self) -> None:
        """典型早期文明：E ≈ 0.074。"""
        e = governance_efficiency(
            bureaucratization=0.2,
            territory_frontier=500,
            territory_core=500,
            tech_engineering=1.0,
            tech_knowledge=1.0,
        )
        assert e == pytest.approx(0.074, abs=0.01)

    def test_mature_empire(self) -> None:
        """成熟帝国：E ≈ 0.22。"""
        e = governance_efficiency(
            bureaucratization=0.6,
            territory_frontier=2000,
            territory_core=1000,
            tech_engineering=2.0,
            tech_knowledge=2.0,
        )
        assert e == pytest.approx(0.22, abs=0.01)

    def test_highly_developed(self) -> None:
        """高度发达：E ≈ 0.68。"""
        e = governance_efficiency(
            bureaucratization=0.8,
            territory_frontier=1000,
            territory_core=2000,
            tech_engineering=3.0,
            tech_knowledge=3.0,
        )
        assert e == pytest.approx(0.68, abs=0.01)


class TestGovernanceBoundaries:
    """边界输入不应崩溃或产生非法值。"""

    def test_all_frontier_zero_core(self) -> None:
        """核心领土为 0（全是边疆）：使用 max(core,1)，不崩溃。"""
        e = governance_efficiency(
            bureaucratization=0.5,
            territory_frontier=1000,
            territory_core=0,
            tech_engineering=1.0,
            tech_knowledge=1.0,
        )
        assert not math.isnan(e)
        assert not math.isinf(e)
        assert 0.0 <= e <= 1.0

    def test_zero_tech(self) -> None:
        """技术为 0：V_norm=0，边疆衰减为 0。"""
        e = governance_efficiency(
            bureaucratization=0.5,
            territory_frontier=100,
            territory_core=100,
            tech_engineering=0.0,
            tech_knowledge=0.0,
        )
        assert e == 0.0

    def test_zero_frontier(self) -> None:
        """无边疆：E = bureaucratization。"""
        e = governance_efficiency(
            bureaucratization=0.5,
            territory_frontier=0,
            territory_core=100,
            tech_engineering=1.0,
            tech_knowledge=1.0,
        )
        assert e == pytest.approx(0.5, abs=1e-9)

    def test_extreme_bureaucratization(self) -> None:
        e = governance_efficiency(0.0, 500, 500, 1.0, 1.0)
        assert e == 0.0
        e2 = governance_efficiency(1.0, 500, 500, 1.0, 1.0)
        assert 0.0 <= e2 <= 1.0
