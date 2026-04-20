from sqlalchemy.orm import Session
from .models import Session as DBSession, AgentTask, Result
import uuid

class StateStore:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_input: str, graph_state: dict = None):
        session = DBSession(user_input=user_input, graph_state=graph_state, status='active')
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update_session_state(self, session_id: str, graph_state: dict, status: str = None):
        session = self.db.query(DBSession).filter(DBSession.id == session_id).first()
        if session:
            session.graph_state = graph_state
            if status:
                session.status = status
            self.db.commit()

    def create_task(self, session_id: str, sender: str, receiver: str, task_payload: dict):
        task = AgentTask(session_id=session_id, sender=sender, receiver=receiver, task_payload=task_payload, status='pending')
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task_status(self, task_id: str, status: str):
        task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if task:
            task.status = status
            self.db.commit()

    def save_results(self, session_id: str, flight_options: list, hotel_options: list, combined: list, selected: dict = None):
        result = Result(session_id=session_id, flight_options=flight_options, hotel_options=hotel_options, combined=combined, selected=selected)
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result