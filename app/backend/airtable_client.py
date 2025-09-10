import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLES
from db_models import (
    HypotheticalQuestion,
    HypotheticalQuestionCreate,
    HypotheticalQuestionUpdate,
    Pitch,
    PitchCreate,
    PitchUpdate,
    TrainingSession,
    TrainingSessionCreate,
    TrainingSessionUpdate,
    User,
    UserCreate,
    UserInDB,
    UserUpdate,
)
from pyairtable import Api
from pyairtable.formulas import match


class AirtableClient:
    def __init__(self):
        self.api = Api(AIRTABLE_API_KEY)
        self.base = self.api.base(AIRTABLE_BASE_ID)

        self.users_table = self.base.table(AIRTABLE_TABLES['users'])
        self.pitches_table = self.base.table(AIRTABLE_TABLES['pitches'])
        self.training_sessions_table = self.base.table(AIRTABLE_TABLES['training_sessions'])
        self.hypothetical_questions_table = self.base.table(AIRTABLE_TABLES['hypothetical_questions'])

    def _prepare_user_for_airtable(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        airtable_data = {}

        if 'id' in user_data:
            airtable_data['id'] = user_data['id']
        if 'email' in user_data:
            airtable_data['email'] = user_data['email']
        if 'full_name' in user_data:
            airtable_data['full_name'] = user_data['full_name']
        if 'hashed_password' in user_data:
            airtable_data['hashed_password'] = user_data['hashed_password']
        if 'is_active' in user_data:
            airtable_data['is_active'] = user_data['is_active']
        if 'created_at' in user_data:
            airtable_data['created_at'] = (
                user_data['created_at'].isoformat()
                if isinstance(user_data['created_at'], datetime)
                else user_data['created_at']
            )
        if 'updated_at' in user_data:
            airtable_data['updated_at'] = (
                user_data['updated_at'].isoformat()
                if isinstance(user_data['updated_at'], datetime)
                else user_data['updated_at']
            )

        return airtable_data

    def _user_from_airtable(self, record: Dict[str, Any]) -> UserInDB:
        """Преобразует запись Airtable в модель пользователя"""
        fields = record['fields']
        return UserInDB(
            id=fields.get('id', ''),
            email=fields.get('email', ''),
            full_name=fields.get('full_name', ''),
            hashed_password=fields.get('hashed_password', ''),
            is_active=fields.get('is_active', True),
            created_at=datetime.fromisoformat(fields.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(fields.get('updated_at', datetime.now().isoformat())),
        )

    def _prepare_pitch_for_airtable(self, pitch_data: Dict[str, Any]) -> Dict[str, Any]:
        airtable_data = {}

        if 'id' in pitch_data:
            airtable_data['id'] = pitch_data['id']
        if 'user_id' in pitch_data:
            airtable_data['user_id'] = pitch_data['user_id']
        if 'title' in pitch_data:
            airtable_data['title'] = pitch_data['title']
        if 'content' in pitch_data:
            airtable_data['content'] = pitch_data['content']
        if 'planned_duration_minutes' in pitch_data:
            airtable_data['planned_duration_minutes'] = pitch_data['planned_duration_minutes']
        if 'description' in pitch_data:
            airtable_data['description'] = pitch_data['description']
        if 'tags' in pitch_data and pitch_data['tags'] is not None:
            airtable_data['tags'] = pitch_data['tags'] if pitch_data['tags'] else []
        if 'presentation_file_name' in pitch_data:
            airtable_data['presentation_file_name'] = pitch_data['presentation_file_name']
        if 'presentation_file_path' in pitch_data:
            airtable_data['presentation_file_path'] = pitch_data['presentation_file_path']
        if 'created_at' in pitch_data:
            airtable_data['created_at'] = (
                pitch_data['created_at'].isoformat()
                if isinstance(pitch_data['created_at'], datetime)
                else pitch_data['created_at']
            )
        if 'updated_at' in pitch_data:
            airtable_data['updated_at'] = (
                pitch_data['updated_at'].isoformat()
                if isinstance(pitch_data['updated_at'], datetime)
                else pitch_data['updated_at']
            )

        return airtable_data

    def _pitch_from_airtable(self, record: Dict[str, Any]) -> Pitch:
        fields = record['fields']
        return Pitch(
            id=fields.get('id', ''),
            user_id=fields.get('user_id', ''),
            title=fields.get('title', ''),
            content=fields.get('content', ''),
            planned_duration_minutes=fields.get('planned_duration_minutes', 0),
            description=fields.get('description'),
            tags=fields.get('tags', []),
            presentation_file_name=fields.get('presentation_file_name'),
            presentation_file_path=fields.get('presentation_file_path'),
            created_at=datetime.fromisoformat(fields.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(fields.get('updated_at', datetime.now().isoformat())),
        )

    def _prepare_training_session_for_airtable(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        airtable_data = {}

        if 'id' in session_data:
            airtable_data['id'] = session_data['id']
        if 'pitch_id' in session_data:
            airtable_data['pitch_id'] = session_data['pitch_id']
        if 'training_type' in session_data:
            airtable_data['training_type'] = session_data['training_type']
        if 'duration_seconds' in session_data:
            airtable_data['duration_seconds'] = session_data['duration_seconds']
        if 'video_file_path' in session_data:
            airtable_data['video_file_path'] = session_data['video_file_path']
        if 'audio_file_path' in session_data:
            airtable_data['audio_file_path'] = session_data['audio_file_path']
        if 'analysis_results' in session_data:
            airtable_data['analysis_results'] = (
                str(session_data['analysis_results']) if session_data['analysis_results'] else None
            )
        if 'overall_score' in session_data:
            airtable_data['overall_score'] = session_data['overall_score']
        if 'notes' in session_data:
            airtable_data['notes'] = session_data['notes']
        if 'created_at' in session_data:
            airtable_data['created_at'] = (
                session_data['created_at'].isoformat()
                if isinstance(session_data['created_at'], datetime)
                else session_data['created_at']
            )
        if 'updated_at' in session_data:
            airtable_data['updated_at'] = (
                session_data['updated_at'].isoformat()
                if isinstance(session_data['updated_at'], datetime)
                else session_data['updated_at']
            )

        return airtable_data

    def _training_session_from_airtable(self, record: Dict[str, Any]) -> TrainingSession:
        fields = record['fields']

        analysis_results = None
        if fields.get('analysis_results'):
            try:
                import json

                analysis_results = json.loads(fields['analysis_results'])
            except:
                analysis_results = None

        return TrainingSession(
            id=fields.get('id', ''),
            pitch_id=fields.get('pitch_id', ''),
            training_type=fields.get('training_type', 'video_upload'),
            duration_seconds=fields.get('duration_seconds'),
            video_file_path=fields.get('video_file_path'),
            audio_file_path=fields.get('audio_file_path'),
            analysis_results=analysis_results,
            overall_score=fields.get('overall_score'),
            notes=fields.get('notes'),
            created_at=datetime.fromisoformat(fields.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(fields.get('updated_at', datetime.now().isoformat())),
        )

    def _prepare_question_for_airtable(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        airtable_data = {}

        if 'id' in question_data:
            airtable_data['id'] = question_data['id']
        if 'pitch_id' in question_data:
            airtable_data['pitch_id'] = question_data['pitch_id']
        if 'question_text' in question_data:
            airtable_data['question_text'] = question_data['question_text']
        if 'category' in question_data:
            airtable_data['category'] = question_data['category']
        if 'difficulty' in question_data:
            airtable_data['difficulty'] = question_data['difficulty']
        if 'suggested_answer' in question_data:
            airtable_data['suggested_answer'] = question_data['suggested_answer']
        if 'context' in question_data:
            airtable_data['context'] = question_data['context']
        if 'preparation_tips' in question_data and question_data['preparation_tips'] is not None:
            airtable_data['preparation_tips'] = (
                question_data['preparation_tips'] if question_data['preparation_tips'] else []
            )
        if 'created_at' in question_data:
            airtable_data['created_at'] = (
                question_data['created_at'].isoformat()
                if isinstance(question_data['created_at'], datetime)
                else question_data['created_at']
            )
        if 'updated_at' in question_data:
            airtable_data['updated_at'] = (
                question_data['updated_at'].isoformat()
                if isinstance(question_data['updated_at'], datetime)
                else question_data['updated_at']
            )

        return airtable_data

    def _question_from_airtable(self, record: Dict[str, Any]) -> HypotheticalQuestion:
        fields = record['fields']
        return HypotheticalQuestion(
            id=fields.get('id', ''),
            pitch_id=fields.get('pitch_id', ''),
            question_text=fields.get('question_text', ''),
            category=fields.get('category', 'business'),
            difficulty=fields.get('difficulty', 'easy'),
            suggested_answer=fields.get('suggested_answer'),
            context=fields.get('context'),
            preparation_tips=fields.get('preparation_tips', []),
            created_at=datetime.fromisoformat(fields.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(fields.get('updated_at', datetime.now().isoformat())),
        )

    def create_user(self, user_create: UserCreate, user_id: Optional[str] = None) -> UserInDB:
        if not user_id:
            user_id = str(uuid.uuid4())

        now = datetime.now()
        user_data = {
            'id': user_id,
            'email': user_create.email,
            'full_name': user_create.full_name,
            'hashed_password': user_create.password,
            'is_active': user_create.is_active,
            'created_at': now,
            'updated_at': now,
        }

        airtable_data = self._prepare_user_for_airtable(user_data)
        record = self.users_table.create(airtable_data, typecast=True)
        return self._user_from_airtable(record)

    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        try:
            records = self.users_table.all(formula=match({'id': user_id}))
            if records:
                return self._user_from_airtable(records[0])
            return None
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        try:
            records = self.users_table.all(formula=match({'email': email}))
            if records:
                return self._user_from_airtable(records[0])
            return None
        except Exception:
            return None

    def get_all_users(self) -> List[UserInDB]:
        try:
            records = self.users_table.all()
            return [self._user_from_airtable(record) for record in records]
        except Exception:
            return []

    def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        try:
            records = self.users_table.all(formula=match({'id': user_id}))
            if not records:
                return None

            record_id = records[0]['id']
            update_data = user_update.model_dump(exclude_unset=True)
            update_data['updated_at'] = datetime.now()

            airtable_data = self._prepare_user_for_airtable(update_data)
            updated_record = self.users_table.update(record_id, airtable_data, typecast=True)
            return self._user_from_airtable(updated_record)
        except Exception:
            return None

    def delete_user(self, user_id: str) -> bool:
        try:
            records = self.users_table.all(formula=match({'id': user_id}))
            if records:
                self.users_table.delete(records[0]['id'])
                return True
            return False
        except Exception:
            return False

    def create_pitch(self, pitch_create: PitchCreate, user_id: str, pitch_id: Optional[str] = None) -> Pitch:
        if not pitch_id:
            pitch_id = str(uuid.uuid4())

        now = datetime.now()
        pitch_data = pitch_create.model_dump()
        pitch_data.update({'id': pitch_id, 'user_id': user_id, 'created_at': now, 'updated_at': now})

        airtable_data = self._prepare_pitch_for_airtable(pitch_data)
        record = self.pitches_table.create(airtable_data, typecast=True)
        return self._pitch_from_airtable(record)

    def get_pitch_by_id(self, pitch_id: str) -> Optional[Pitch]:
        try:
            records = self.pitches_table.all(formula=match({'id': pitch_id}))
            if records:
                return self._pitch_from_airtable(records[0])
            return None
        except Exception:
            return None

    def get_pitches_by_user_id(self, user_id: str) -> List[Pitch]:
        try:
            records = self.pitches_table.all(formula=match({'user_id': user_id}))
            return [self._pitch_from_airtable(record) for record in records]
        except Exception:
            return []

    def get_all_pitches(self) -> List[Pitch]:
        try:
            records = self.pitches_table.all()
            return [self._pitch_from_airtable(record) for record in records]
        except Exception:
            return []

    def update_pitch(self, pitch_id: str, pitch_update: PitchUpdate) -> Optional[Pitch]:
        try:
            records = self.pitches_table.all(formula=match({'id': pitch_id}))
            if not records:
                return None

            record_id = records[0]['id']
            update_data = pitch_update.model_dump(exclude_unset=True)
            update_data['updated_at'] = datetime.now()

            airtable_data = self._prepare_pitch_for_airtable(update_data)
            updated_record = self.pitches_table.update(record_id, airtable_data, typecast=True)
            return self._pitch_from_airtable(updated_record)
        except Exception:
            return None

    def delete_pitch(self, pitch_id: str) -> bool:
        try:
            records = self.pitches_table.all(formula=match({'id': pitch_id}))
            if records:
                self.pitches_table.delete(records[0]['id'])
                return True
            return False
        except Exception:
            return False

    def create_training_session(
        self, session_create: TrainingSessionCreate, session_id: Optional[str] = None
    ) -> TrainingSession:
        if not session_id:
            session_id = str(uuid.uuid4())

        now = datetime.now()
        session_data = session_create.model_dump()
        session_data.update({'id': session_id, 'created_at': now, 'updated_at': now})

        if session_data.get('analysis_results'):
            import json

            session_data['analysis_results'] = json.dumps(session_data['analysis_results'], ensure_ascii=False)

        airtable_data = self._prepare_training_session_for_airtable(session_data)
        record = self.training_sessions_table.create(airtable_data, typecast=True)
        return self._training_session_from_airtable(record)

    def get_training_session_by_id(self, session_id: str) -> Optional[TrainingSession]:
        try:
            records = self.training_sessions_table.all(formula=match({'id': session_id}))
            if records:
                return self._training_session_from_airtable(records[0])
            return None
        except Exception:
            return None

    def get_training_sessions_by_pitch_id(self, pitch_id: str) -> List[TrainingSession]:
        try:
            records = self.training_sessions_table.all(formula=match({'pitch_id': pitch_id}))
            return [self._training_session_from_airtable(record) for record in records]
        except Exception:
            return []

    def get_all_training_sessions(self) -> List[TrainingSession]:
        try:
            records = self.training_sessions_table.all()
            return [self._training_session_from_airtable(record) for record in records]
        except Exception:
            return []

    def update_training_session(
        self, session_id: str, session_update: TrainingSessionUpdate
    ) -> Optional[TrainingSession]:
        try:
            records = self.training_sessions_table.all(formula=match({'id': session_id}))
            if not records:
                return None

            record_id = records[0]['id']
            update_data = session_update.model_dump(exclude_unset=True)
            update_data['updated_at'] = datetime.now()

            if update_data.get('analysis_results'):
                import json

                update_data['analysis_results'] = json.dumps(update_data['analysis_results'], ensure_ascii=False)

            airtable_data = self._prepare_training_session_for_airtable(update_data)
            updated_record = self.training_sessions_table.update(record_id, airtable_data, typecast=True)
            return self._training_session_from_airtable(updated_record)
        except Exception:
            return None

    def delete_training_session(self, session_id: str) -> bool:
        try:
            records = self.training_sessions_table.all(formula=match({'id': session_id}))
            if records:
                self.training_sessions_table.delete(records[0]['id'])
                return True
            return False
        except Exception:
            return False

    def create_hypothetical_question(
        self, question_create: HypotheticalQuestionCreate, question_id: Optional[str] = None
    ) -> HypotheticalQuestion:
        if not question_id:
            question_id = str(uuid.uuid4())

        now = datetime.now()
        question_data = question_create.model_dump()
        question_data.update({'id': question_id, 'created_at': now, 'updated_at': now})

        airtable_data = self._prepare_question_for_airtable(question_data)
        record = self.hypothetical_questions_table.create(airtable_data, typecast=True)
        return self._question_from_airtable(record)

    def get_hypothetical_question_by_id(self, question_id: str) -> Optional[HypotheticalQuestion]:
        try:
            records = self.hypothetical_questions_table.all(formula=match({'id': question_id}))
            if records:
                return self._question_from_airtable(records[0])
            return None
        except Exception:
            return None

    def get_hypothetical_questions_by_pitch_id(self, pitch_id: str) -> List[HypotheticalQuestion]:
        try:
            records = self.hypothetical_questions_table.all(formula=match({'pitch_id': pitch_id}))
            return [self._question_from_airtable(record) for record in records]
        except Exception:
            return []

    def get_all_hypothetical_questions(self) -> List[HypotheticalQuestion]:
        try:
            records = self.hypothetical_questions_table.all()
            return [self._question_from_airtable(record) for record in records]
        except Exception:
            return []

    def update_hypothetical_question(
        self, question_id: str, question_update: HypotheticalQuestionUpdate
    ) -> Optional[HypotheticalQuestion]:
        try:
            records = self.hypothetical_questions_table.all(formula=match({'id': question_id}))
            if not records:
                return None

            record_id = records[0]['id']
            update_data = question_update.model_dump(exclude_unset=True)
            update_data['updated_at'] = datetime.now()

            airtable_data = self._prepare_question_for_airtable(update_data)
            updated_record = self.hypothetical_questions_table.update(record_id, airtable_data, typecast=True)
            return self._question_from_airtable(updated_record)
        except Exception:
            return None

    def delete_hypothetical_question(self, question_id: str) -> bool:
        try:
            records = self.hypothetical_questions_table.all(formula=match({'id': question_id}))
            if records:
                self.hypothetical_questions_table.delete(records[0]['id'])
                return True
            return False
        except Exception:
            return False


airtable_client = AirtableClient()
