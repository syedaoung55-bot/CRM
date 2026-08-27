from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from typing import List
from .. import schemas, models, oauth2
from ..permissions import require_admin, check_team_permission  , scoped, log_field_changes

router = APIRouter(
    prefix="/api/v1/teams",
    tags = ['Teams'])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.TeamOut)
def cretae_team(team: schemas.TeamCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)
    if team.manager_id:
        manager = db.query(models.User).filter(models.User.id == team.manager_id,
                            models.User.company_id == current_user.company_id).first()

        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                    detail="Manager not found.")

        if manager.role.value != models.UserRole.manager:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail="manager_id must refrence a user with manager role.")

    new_team = models.Team(
        name = team.name,
        manager_id = team.manager_id,
        company_id = current_user.company_id
    )

    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return new_team


@router.get("/", response_model=List[schemas.TeamOut])
def get_all_teams(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    return scoped(db.query(models.Team), models.Team, current_user).all()

@router.get("/{id}", response_model=schemas.TeamOut)
def get_team(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    team = scoped(db.query(models.Team), models.Team, current_user).filter(models.Team.id == id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Team with id {id} is not found.")

    return team

@router.patch("/{id}/members/{user_id}", response_model=schemas.UserOut)
def add_member(id: int, user_id: int, db: Session = Depends(get_db), 
            current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    team = scoped(db.query(models.Team), models.Team, current_user).filter(models.Team.id == id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Team with id {id} is not found.")
    member = db.query(models.User).filter(models.User.id == user_id, 
                            models.User.company_id == current_user.company_id).first()
    if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                        detail="User not found.")

    member.team_id = id  # type: ignore

    db.commit()
    db.refresh(member)
    return member


@router.put("/{id}", response_model=schemas.TeamOut)
def update_team(id: int, team_update: schemas.TeamUpdate, db: Session = Depends(get_db), 
                current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    team = scoped(db.query(models.Team), models.Team, current_user).filter(models.Team.id == id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Team with id {id} is not found.")
    update_data = team_update.model_dump(exclude_unset=True)

    if "manager_id" in update_data and update_data["manager_id"] is not None:
        manager = db.query(models.User).filter(models.User.id == update_data["manager_id"],
                                    models.User.company_id == current_user.company_id).first()
        
        if not manager:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                        detail="Manager not found.")

        if manager.role.value != models.UserRole.manager:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                        detail="manager_id must refrence a user with manager role.")

    before = {"name": team.name, "manager_id": team.manager_id}

    for field, value in update_data.items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)

    after = {"name": team.name, "manager_id": team.manager_id}
    log_field_changes(db, "teams", team.id, before, after, current_user.id, current_user.company_id) #type: ignore

    return team

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    team = scoped(db.query(models.Team), models.Team, current_user).filter(models.Team.id == id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                        detail=f"Team with id {id} is not found.")

    db.delete(team)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)