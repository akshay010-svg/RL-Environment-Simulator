"""
Task model – a sub-task belonging to a Ticket.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="tasks")

    def __repr__(self) -> str:
        done = "✓" if self.is_completed else "✗"
        return f"<Task id={self.id} [{done}] ticket_id={self.ticket_id}>"
