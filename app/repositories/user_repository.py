"""
User repository — all database operations on the users table.

Pattern: pass an AsyncSession to the constructor.
The session is owned by the caller (typically the FastAPI request).
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.models import User


class UserRepository:
    """
    Repository for User entities.

    Methods do NOT commit — the caller (typically the request scope)
    owns transaction lifecycle.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_slack_id(self, slack_user_id: str) -> User | None:
        """
        Get a user by their Slack ID.

        Returns the User or None if not found.
        """
        result = await self.session.execute(
            select(User).where(User.slack_user_id == slack_user_id)
        )
        return result.scalar_one_or_none()

    async def create(
            self,
            slack_user_id: str,
            email: str | None = None,
            display_name: str | None = None,
            role: str = "employee",
    ) -> User:
        """
        Create a new user.

        Returns the created User.
        """
        user = User(
            slack_user_id=slack_user_id,
            email=email,
            display_name=display_name,
            role=role,
        )
        self.session.add(user)
        await self.session.flush()  # Flush to get the ID populated
        return user

    async def get_or_create_by_slack_id(
        self,
        slack_user_id: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> tuple[User, bool]:
        """
        Get a user by Slack ID, or create if not exists.

        Returns:
            (user, was_created): user object + bool flag whether new record was created.
        """
        existing_user = await self.get_by_slack_id(slack_user_id)
        if existing_user:
            return existing_user, False
        new_user = await self.create(
            slack_user_id=slack_user_id,
            email=email,
            display_name=display_name,
        )
        return new_user, True
