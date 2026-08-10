import pytest
from fastapi import HTTPException

from app.backend.models.material import Material
from app.backend.schemas.material import MaterialImport
from app.backend.services.material_service import MaterialService


@pytest.fixture
def mock_import(monkeypatch):
    """Substitui a chamada de verdade ao Google Docs por um retorno fixo --
    os testes de integração não devem depender de rede/credencial real."""

    async def _fake_import_material_html(url: str) -> tuple[str, str]:
        return "fake-doc-id-123", "<p>Conteudo sanitizado de mentirinha</p>"

    monkeypatch.setattr(
        "app.backend.services.material_service.import_material_html",
        _fake_import_material_html,
    )
    return _fake_import_material_html


async def test_import_creates_material(db_session, clinic, admin_user, mock_import):
    service = MaterialService(db_session)
    data = MaterialImport(
        title="Respiração diafragmática", level=1, source_url="https://docs.google.com/document/d/abc/edit"
    )

    material = await service.import_from_google_docs(clinic.id, data, admin_user)

    assert material.id is not None
    assert material.clinic_id == clinic.id
    assert material.title == "Respiração diafragmática"
    assert material.source_document_id == "fake-doc-id-123"
    assert material.content_html == "<p>Conteudo sanitizado de mentirinha</p>"
    assert material.imported_by == admin_user.id


async def test_reimport_overwrites_content_and_updates_metadata(
    db_session, clinic, admin_user, professional_user, mock_import, monkeypatch
):
    service = MaterialService(db_session)
    data = MaterialImport(title="Título", level=1, source_url="https://docs.google.com/document/d/abc/edit")
    material = await service.import_from_google_docs(clinic.id, data, admin_user)
    original_imported_at = material.imported_at

    async def _fake_updated(url: str) -> tuple[str, str]:
        return "fake-doc-id-123", "<p>Conteudo atualizado</p>"

    monkeypatch.setattr("app.backend.services.material_service.import_material_html", _fake_updated)

    updated = await service.reimport(clinic.id, material.id, professional_user)

    assert updated.content_html == "<p>Conteudo atualizado</p>"
    assert updated.imported_by == professional_user.id
    assert updated.imported_at >= original_imported_at


async def test_list_filters_materials_by_patient_level(
    db_session, clinic, admin_user, patient, patient_user, mock_import
):
    service = MaterialService(db_session)
    patient.level = 2
    db_session.add(patient)
    await db_session.commit()

    for level in (1, 2, 3):
        db_session.add(
            Material(
                clinic_id=clinic.id,
                title=f"Material nivel {level}",
                level=level,
                content_html="<p>x</p>",
                source_url="https://docs.google.com/document/d/x/edit",
                source_document_id="x",
                imported_by=admin_user.id,
            )
        )
    await db_session.commit()

    materials = await service.list(clinic.id, patient_user)

    titles = {m.title for m in materials}
    assert titles == {"Material nivel 1", "Material nivel 2"}
    assert "Material nivel 3" not in titles


async def test_list_staff_sees_all_levels_regardless_of_patient(db_session, clinic, admin_user, mock_import):
    service = MaterialService(db_session)
    for level in (1, 5, 10):
        db_session.add(
            Material(
                clinic_id=clinic.id,
                title=f"Material nivel {level}",
                level=level,
                content_html="<p>x</p>",
                source_url="https://docs.google.com/document/d/x/edit",
                source_document_id="x",
                imported_by=admin_user.id,
            )
        )
    await db_session.commit()

    materials = await service.list(clinic.id, admin_user)

    assert len(materials) == 3


async def test_get_blocks_patient_from_material_above_their_level(
    db_session, clinic, admin_user, patient, patient_user
):
    patient.level = 1
    db_session.add(patient)
    await db_session.commit()

    high_level_material = Material(
        clinic_id=clinic.id,
        title="Avançado",
        level=5,
        content_html="<p>x</p>",
        source_url="https://docs.google.com/document/d/x/edit",
        source_document_id="x",
        imported_by=admin_user.id,
    )
    db_session.add(high_level_material)
    await db_session.commit()
    await db_session.refresh(high_level_material)

    service = MaterialService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.get(clinic.id, high_level_material.id, patient_user)

    assert exc_info.value.status_code == 403


async def test_get_allows_patient_to_material_at_their_level(db_session, clinic, admin_user, patient, patient_user):
    patient.level = 3
    db_session.add(patient)
    await db_session.commit()

    material = Material(
        clinic_id=clinic.id,
        title="No nível certo",
        level=3,
        content_html="<p>x</p>",
        source_url="https://docs.google.com/document/d/x/edit",
        source_document_id="x",
        imported_by=admin_user.id,
    )
    db_session.add(material)
    await db_session.commit()
    await db_session.refresh(material)

    service = MaterialService(db_session)
    fetched = await service.get(clinic.id, material.id, patient_user)

    assert fetched.id == material.id


async def test_material_from_other_clinic_is_not_returned(db_session, clinic, admin_user):
    from app.backend.models.clinic import Clinic

    other_clinic = Clinic(name="Outra clínica", slug="outra-clinica")
    db_session.add(other_clinic)
    await db_session.commit()
    await db_session.refresh(other_clinic)

    other_material = Material(
        clinic_id=other_clinic.id,
        title="De outra clínica",
        level=1,
        content_html="<p>x</p>",
        source_url="https://docs.google.com/document/d/x/edit",
        source_document_id="x",
        imported_by=admin_user.id,
    )
    db_session.add(other_material)
    await db_session.commit()

    service = MaterialService(db_session)
    materials = await service.list(clinic.id, admin_user)

    assert all(m.clinic_id == clinic.id for m in materials)
    assert "De outra clínica" not in {m.title for m in materials}


async def test_soft_delete_hides_material_from_list(db_session, clinic, admin_user, mock_import):
    service = MaterialService(db_session)
    data = MaterialImport(title="Vai ser arquivado", level=1, source_url="https://docs.google.com/document/d/abc/edit")
    material = await service.import_from_google_docs(clinic.id, data, admin_user)

    await service.soft_delete(clinic.id, material.id, admin_user)

    materials = await service.list(clinic.id, admin_user)
    assert material.id not in [m.id for m in materials]
