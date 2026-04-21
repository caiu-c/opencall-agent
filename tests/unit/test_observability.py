from __future__ import annotations

from opencall_agent.observability import scrub


def test_scrub_masks_cpf() -> None:
    assert scrub("CPF 123.456.789-00 do cliente") == "CPF [CPF] do cliente"
    assert scrub("cpf sem pontuação 12345678900 fim") == "cpf sem pontuação [CPF] fim"


def test_scrub_masks_email() -> None:
    assert scrub("mande para joao.silva+dev@example.com.br hoje") == (
        "mande para [EMAIL] hoje"
    )


def test_scrub_masks_phone() -> None:
    assert scrub("ligue (11) 98765-4321") == "ligue [PHONE]"
    assert scrub("fixo 11 3245-6789") == "fixo [PHONE]"


def test_scrub_leaves_non_pii_intact() -> None:
    assert scrub("RDC 44/2009 da ANVISA") == "RDC 44/2009 da ANVISA"


def test_scrub_handles_empty() -> None:
    assert scrub("") == ""
