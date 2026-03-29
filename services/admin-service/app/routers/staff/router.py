from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.models.enums import Roles
from app.services.admin_service import create_staff_user, list_users, set_user_status
from app.routers.schemas import StaffCreate, StaffUpdate, UserStatusPayload

router = APIRouter()


@router.get("/users")
async def users_list(user=Depends(require_roles(Roles.ADMIN))):
    return await list_users()


@router.post("/users/create")
async def users_create(payload: StaffCreate, user=Depends(require_roles(Roles.ADMIN))):
    return await create_staff_user(
        payload.email,
        payload.full_name,
        payload.password,
        payload.role,
        phone=payload.phone,
        department=payload.department,
        designation=payload.designation,
        employee_code=payload.employee_code,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
    )


@router.put("/users/{user_id}/status")
async def users_set_status(user_id: str, payload: UserStatusPayload, user=Depends(require_roles(Roles.ADMIN))):
    return await set_user_status(user_id, payload.is_active)


@router.post("/create-staff")
async def create_staff(payload: StaffCreate, user=Depends(require_roles(Roles.ADMIN))):
    return await create_staff_user(
        payload.email,
        payload.full_name,
        payload.password,
        payload.role,
        phone=payload.phone,
        department=payload.department,
        designation=payload.designation,
        employee_code=payload.employee_code,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
    )


@router.put("/users/{user_id}")
async def users_update(user_id: str, payload: StaffUpdate, user=Depends(require_roles(Roles.ADMIN))):
    from app.services.admin_service import update_staff_user

    return await update_staff_user(user_id, payload.dict(exclude_unset=True))


@router.delete("/users/{user_id}")
async def users_delete(user_id: str, user=Depends(require_roles(Roles.ADMIN))):
    from app.services.admin_service import delete_staff_user

    return await delete_staff_user(user_id)
