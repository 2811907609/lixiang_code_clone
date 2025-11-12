from dataclasses import dataclass

from sysutils.xtypes import Renewable


def test_renewable_class():

    @dataclass
    class TestRenewable(Renewable):
        attr1: int = 10
        attr2: str = "default"
        attr3: str = None

    old_instance = TestRenewable()
    old_instance.attr1 = 20
    old_instance.attr2 = "changed"
    old_instance.attr3 = "a3"
    old_instance.attr4 = "a4"

    new_instance = TestRenewable.renew(old_instance)

    assert new_instance.attr1 == 20
    assert new_instance.attr2 == "changed"
    assert new_instance.attr3 == "a3"
    assert getattr(new_instance, "attr4", None) is None
    assert isinstance(new_instance, TestRenewable)
