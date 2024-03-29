# -*- coding: utf-8 -*-
import datetime
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import ValidationError

from app.pydantic_models import (
    RawDataListModelInput, BulkInsertOutputModel
)
from app.dependencies import get_current_active_user
from app.models import (
    User, RawPatientRecord, RawPatientCondition, DataSource
)


router = APIRouter(prefix="/raw", tags=["Entidades RAW (Formato Raw/Bruto)"])


RawPatientConditionOutput = pydantic_model_creator(
    RawPatientCondition, name="RawPatientConditionOutput",
    exclude=("is_dirty",)
)

RawPatientRecordOutput = pydantic_model_creator(
    RawPatientRecord, name="RawPatientRecordOutput",
    exclude=("is_dirty",)
)


@router.get("/patientrecords/fromEventDatetime")
async def get_raw_patientrecords_from_event_datetime(
    _: Annotated[User, Depends(get_current_active_user)],
    start_datetime: datetime.datetime = datetime.datetime.now() -
    datetime.timedelta(hours=1),
    end_datetime: datetime.datetime = datetime.datetime.now(),
    datasource_system: str = None,
) -> list[RawPatientRecordOutput]:

    filtered = RawPatientRecord.filter(
        source_updated_at__gte=start_datetime,
        source_updated_at__lt=end_datetime,
        is_dirty__not=True
    )

    if datasource_system is not None:
        filtered = filtered.filter(
            data_source__system=datasource_system
        )
    return await RawPatientRecordOutput.from_queryset(filtered)

@router.get("/patientrecords/fromInsertionDatetime")
async def get_raw_patientrecords_from_insertion_datetime(
    _: Annotated[User, Depends(get_current_active_user)],
    start_datetime: datetime.datetime = datetime.datetime.now() -
    datetime.timedelta(hours=1),
    end_datetime: datetime.datetime = datetime.datetime.now(),
    datasource_system: str = None,
) -> list[RawPatientRecordOutput]:

    filtered = RawPatientRecord.filter(
        updated_at__gte=start_datetime,
        updated_at__lt=end_datetime,
        is_dirty__not=True
    )

    if datasource_system is not None:
        filtered = filtered.filter(
            data_source__system=datasource_system
        )
    return await RawPatientRecordOutput.from_queryset(filtered)


@router.post("/patientrecords", status_code=201)
async def create_raw_patientrecords(
    _: Annotated[User, Depends(get_current_active_user)],
    raw_data: RawDataListModelInput,
) -> BulkInsertOutputModel:

    raw_data = raw_data.dict()

    cnes = raw_data.pop("cnes")
    records = raw_data.pop("data_list")

    try:
        records_to_create = []
        for record in records:
            records_to_create.append(
                RawPatientRecord(
                    patient_cpf=record.get('patient_cpf'),
                    patient_code=record.get('patient_code'),
                    source_updated_at=record.get('source_updated_at'),
                    data=record.get('data'),
                    data_source=await DataSource.get(cnes=cnes)
                )
            )
    except ValidationError as e:
        return HTMLResponse(status_code=400, content=str(e))
    try:
        new_records = await RawPatientRecord.bulk_create(
            records_to_create,
            ignore_conflicts=True
        )
        return {
            'count': len(new_records)
        }
    except asyncpg.exceptions.DeadlockDetectedError as e:
        return HTMLResponse(status_code=400, content=str(e))


@router.post("/patientrecords/setDirty", status_code=200)
async def set_dirty_records(
    _: Annotated[User, Depends(get_current_active_user)],
    raw_record_id_list: list[str],
):
    await RawPatientRecord.filter(id__in=raw_record_id_list).update(is_dirty=True)


@router.get("/patientconditions/fromEventDatetime")
async def get_raw_patientconditions_from_event_datetime(
    _: Annotated[User, Depends(get_current_active_user)],
    start_datetime: datetime.datetime = datetime.datetime.now() -
    datetime.timedelta(hours=1),
    end_datetime: datetime.datetime = datetime.datetime.now(),
    datasource_system: str = None,
) -> list[RawPatientConditionOutput]:

    filtered = RawPatientCondition.filter(
        source_updated_at__gte=start_datetime,
        source_updated_at__lt=end_datetime,
        is_dirty__not=True
    )

    if datasource_system is not None:
        filtered = filtered.filter(
            data_source__system=datasource_system
        )
    return await RawPatientConditionOutput.from_queryset(filtered)

@router.get("/patientconditions/fromInsertionDatetime")
async def get_raw_patientconditions_from_insertion_datetime(
    _: Annotated[User, Depends(get_current_active_user)],
    start_datetime: datetime.datetime = datetime.datetime.now() -
    datetime.timedelta(hours=1),
    end_datetime: datetime.datetime = datetime.datetime.now(),
    datasource_system: str = None,
) -> list[RawPatientConditionOutput]:

    filtered = RawPatientCondition.filter(
        updated_at__gte=start_datetime,
        updated_at__lt=end_datetime,
        is_dirty__not=True
    )

    if datasource_system is not None:
        filtered = filtered.filter(
            data_source__system=datasource_system
        )
    return await RawPatientConditionOutput.from_queryset(filtered)



@router.post("/patientconditions", status_code=201)
async def create_raw_patientconditions(
    _: Annotated[User, Depends(get_current_active_user)],
    raw_data: RawDataListModelInput,
) -> BulkInsertOutputModel:
    raw_data = raw_data.dict()

    cnes = raw_data.pop("cnes")
    conditions = raw_data.pop("data_list")

    try:
        conditions_to_create = []
        for condition in conditions:
            conditions_to_create.append(
                RawPatientCondition(
                    patient_cpf=condition.get('patient_cpf'),
                    patient_code=condition.get('patient_code'),
                    source_updated_at=condition.get('source_updated_at'),
                    data=condition.get('data'),
                    data_source=await DataSource.get(cnes=cnes)
                )
            )
    except ValidationError as e:
        return HTMLResponse(status_code=400, content=str(e))
    try:
        new_conditions = await RawPatientCondition.bulk_create(
            conditions_to_create,
            ignore_conflicts=True
        )
        return {
            'count': len(new_conditions)
        }
    except asyncpg.exceptions.DeadlockDetectedError as e:
        return HTMLResponse(status_code=400, content=str(e))


@router.post("/patientconditions/setDirty", status_code=200)
async def set_dirty_conditions(
    _: Annotated[User, Depends(get_current_active_user)],
    raw_condition_id_list: list[str],
):
    await RawPatientCondition.filter(id__in=raw_condition_id_list).update(is_dirty=True)
