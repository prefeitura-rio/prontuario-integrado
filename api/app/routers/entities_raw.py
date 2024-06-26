# -*- coding: utf-8 -*-
from datetime import (
    datetime as dt,
    timedelta as td,
)
from typing import Annotated, Literal
import asyncpg
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from tortoise.exceptions import ValidationError

from app.pydantic_models import (
    RawDataListModel,
    BulkInsertOutputModel,
    RawDataModel
)
from app.dependencies import get_current_active_user
from app.models import (
    User,
    RawPatientRecord,
    RawPatientCondition,
    DataSource,
    RawEncounter
)


router = APIRouter(prefix="/raw", tags=["Entidades RAW (Formato Raw/Bruto)"])

entity_from_name = {
    "patientrecords": RawPatientRecord,
    "patientconditions": RawPatientCondition,
    "encounter": RawEncounter
}


@router.get("/{entity_name}/{filter_type}")
async def get_raw_data(
    _: Annotated[User, Depends(get_current_active_user)],
    entity_name: Literal["patientrecords", "patientconditions", "encounter"],
    filter_type: Literal["fromEventDatetime", "fromInsertionDatetime"],
    start_datetime: dt = dt.now() - td(hours=1),
    end_datetime: dt = dt.now(),
    datasource_system: Literal["vitai", "vitacare", "smsrio"] = None,
) -> list[RawDataModel]:

    Entity = entity_from_name.get(entity_name)

    if filter_type == "fromEventDatetime":
        filtered = Entity.filter(
            source_updated_at__gte=start_datetime,
            source_updated_at__lt=end_datetime,
            is_valid__not=True,
        )
    elif filter_type == "fromInsertionDatetime":
        filtered = Entity.filter(
            updated_at__gte=start_datetime, updated_at__lt=end_datetime, is_valid__not=True
        )
    else:
        return HTMLResponse(status_code=400, content="Invalid filter type")

    if datasource_system is not None:
        filtered = filtered.filter(data_source__system=datasource_system)

    result = await filtered

    result = [RawDataModel(**dict(record)) for record in result]
    return result


@router.post("/{entity_name}", status_code=201)
async def create_raw_data(
    entity_name: Literal["patientrecords", "patientconditions", "encounter"],
    current_user: Annotated[User, Depends(get_current_active_user)],
    raw_data: RawDataListModel,
) -> BulkInsertOutputModel:

    Entity = entity_from_name.get(entity_name)

    raw_data = raw_data.dict()
    cnes = raw_data.pop("cnes")
    records = raw_data.pop("data_list")

    try:
        records_to_create = []
        for record in records:
            records_to_create.append(
                Entity(
                    patient_cpf=record.get("patient_cpf"),
                    patient_code=record.get("patient_code"),
                    source_updated_at=record.get("source_updated_at"),
                    source_id=record.get("source_id"),
                    data=record.get("data"),
                    data_source=await DataSource.get(cnes=cnes),
                    creator=current_user,
                )
            )
    except ValidationError as e:
        return HTMLResponse(status_code=400, content=str(e))
    try:
        new_records = await Entity.bulk_create(records_to_create, ignore_conflicts=True)
        return {"count": len(new_records)}
    except asyncpg.exceptions.DeadlockDetectedError as e:
        return HTMLResponse(status_code=400, content=str(e))


@router.post("/{entity_name}/setAsInvalid", status_code=200)
async def set_as_invalid_flag_records(
    _: Annotated[User, Depends(get_current_active_user)],
    entity_name: Literal["patientrecords", "patientconditions", "encounter"],
    raw_record_id_list: list[str],
):
    Entity = entity_from_name.get(entity_name)
    await Entity.filter(id__in=raw_record_id_list).update(is_valid=False)