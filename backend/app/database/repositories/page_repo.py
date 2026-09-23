from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.database.models.models import Page, Element, Action, ActionType
from backend.app.api.schemas.page import PageBase, ElementBase, ActionBase

class PageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_url(self, application_id: int, environment_id: int, url: str) -> Optional[Page]:
        return self.db.query(Page).filter(
            Page.application_id == application_id,
            Page.environment_id == environment_id,
            Page.url == url
        ).first()

    def get_or_create(
        self,
        application_id: int,
        environment_id: int,
        url: str,
        title: Optional[str] = None,
        status_code: Optional[int] = None,
        page_type: str = "standard"
    ) -> Page:
        page = self.get_by_url(application_id, environment_id, url)
        now = datetime.utcnow()
        if page:
            page.last_seen_at = now
            if title:
                page.title = title
            if status_code:
                page.status_code = status_code
            self.db.commit()
            self.db.refresh(page)
            return page

        page = Page(
            application_id=application_id,
            environment_id=environment_id,
            url=url,
            title=title,
            status_code=status_code,
            page_type=page_type,
            first_seen_at=now,
            last_seen_at=now
        )
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        return page

    def get_pages_by_app(self, application_id: int) -> List[Page]:
        return self.db.query(Page).filter(Page.application_id == application_id).all()

    def get_page_by_id(self, page_id: int) -> Optional[Page]:
        return self.db.query(Page).filter(Page.id == page_id).first()

    def add_element(self, page_id: int, element_data: ElementBase) -> Element:
        # Check if identical selector already exists on this page to prevent duplicate spam
        existing = self.db.query(Element).filter(
            Element.page_id == page_id,
            Element.selector == element_data.selector
        ).first()
        if existing:
            return existing

        element = Element(
            page_id=page_id,
            element_type=element_data.element_type,
            tag_name=element_data.tag_name,
            selector=element_data.selector,
            text=element_data.text,
            name=element_data.name,
            placeholder=element_data.placeholder,
            role=element_data.role,
            is_interactive=element_data.is_interactive,
            created_at=datetime.utcnow()
        )
        self.db.add(element)
        self.db.commit()
        self.db.refresh(element)
        return element

    def add_action(
        self,
        page_id: int,
        action_type: ActionType,
        element_id: Optional[int] = None,
        action_data: Optional[dict] = None,
        result: Optional[str] = None
    ) -> Action:
        action = Action(
            page_id=page_id,
            element_id=element_id,
            action_type=action_type,
            action_data=action_data,
            result=result,
            created_at=datetime.utcnow()
        )
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        return action

    def get_elements_by_page(self, page_id: int) -> List[Element]:
        return self.db.query(Element).filter(Element.page_id == page_id).all()

    def get_actions_by_page(self, page_id: int) -> List[Action]:
        return self.db.query(Action).filter(Action.page_id == page_id).all()
