from sqlalchemy.orm import Session
from app.models import User, Conversation
from typing import List, Optional
import random
from datetime import datetime, timedelta, timezone

class MatchingService:
    def __init__(self, db: Session):
        self.db = db
    
    def find_match(self, user: User, search_type: str) -> Optional[User]:
        """Tìm người phù hợp để ghép nối"""
        try:
            # Lấy danh sách người có thể match (không phải chính mình)
            # Chỉ match với những user đang trong trạng thái "searching"
            potential_matches = self.db.query(User).filter(
                User.id != user.id,
                User.state == "searching"
            ).all()
            
            if not potential_matches:
                return None
            
            # Kiểm tra lại xem user hiện tại vẫn đang trong trạng thái searching
            # (để tránh race condition)
            current_user = self.db.query(User).filter(User.id == user.id).first()
            if not current_user or current_user.state != "searching":
                return None
            
            # Ưu tiên ghép nối theo sở thích và mong muốn
            best_matches = []
            good_matches = []
            random_matches = []
            
            for potential_match in potential_matches:
                try:
                    # Kiểm tra xem đã có cuộc trò chuyện active nào giữa 2 người này chưa
                    existing_active_conversation = self.db.query(Conversation).filter(
                        ((Conversation.user1_id == user.id) & (Conversation.user2_id == potential_match.id)) |
                        ((Conversation.user1_id == potential_match.id) & (Conversation.user2_id == user.id)),
                        Conversation.is_active == True
                    ).first()
                    
                    # Bỏ qua nếu đang có conversation active với user này
                    if existing_active_conversation:
                        continue
                    
                    # Kiểm tra lại trạng thái của potential_match (tránh race condition)
                    refreshed_match = self.db.query(User).filter(User.id == potential_match.id).first()
                    if not refreshed_match or refreshed_match.state != "searching":
                        continue
                    
                    # Tính điểm phù hợp
                    compatibility_score = self._calculate_compatibility(user, refreshed_match)
                    
                    if compatibility_score >= 0.8:
                        best_matches.append((refreshed_match, compatibility_score))
                    elif compatibility_score >= 0.5:
                        good_matches.append((refreshed_match, compatibility_score))
                    else:
                        random_matches.append((refreshed_match, compatibility_score))
                        
                except Exception as e:
                    print(f"Error processing potential match {potential_match.id}: {e}")
                    continue
            
            # Sắp xếp theo điểm phù hợp
            best_matches.sort(key=lambda x: x[1], reverse=True)
            good_matches.sort(key=lambda x: x[1], reverse=True)
            
            # Ưu tiên ghép nối tốt nhất trước
            if best_matches:
                return best_matches[0][0]
            elif good_matches:
                return good_matches[0][0]
            elif random_matches:
                return random.choice(random_matches)[0]
            
            return None
            
        except Exception as e:
            print(f"Error in find_match: {e}")
            return None
    
    def _calculate_compatibility(self, user1: User, user2: User) -> float:
        """Tính điểm phù hợp giữa 2 người dùng"""
        score = 0.0
        total_factors = 0
        
        # Kiểm tra preference
        if user1.preference == "Tất cả" or user1.preference == user2.gender:
            score += 1.0
        elif user1.preference != user2.gender:
            score += 0.0
        total_factors += 1
        
        if user2.preference == "Tất cả" or user2.preference == user1.gender:
            score += 1.0
        elif user2.preference != user1.gender:
            score += 0.0
        total_factors += 1
        
        # Kiểm tra mục đích tìm kiếm
        if user1.goal == user2.goal:
            score += 1.0
        elif self._are_goals_compatible(user1.goal, user2.goal):
            score += 0.7
        else:
            score += 0.3
        total_factors += 1
        
        # Kiểm tra sở thích chung
        interests1 = user1.get_interests_list()
        interests2 = user2.get_interests_list()
        
        if interests1 and interests2:
            common_interests = set(interests1) & set(interests2)
            if common_interests:
                score += min(len(common_interests) / 2.0, 1.0)  # Tối đa 1 điểm cho sở thích
            total_factors += 1
        
        return score / total_factors if total_factors > 0 else 0.0
    
    def _are_goals_compatible(self, goal1: str, goal2: str) -> bool:
        """Kiểm tra xem 2 mục đích có tương thích không"""
        compatible_pairs = [
            ("Một mối quan hệ nhẹ nhàng, vui vẻ", "Chưa chắc, muốn khám phá thêm"),
            ("Một mối quan hệ nghiêm túc", "Kết hôn"),
            ("Một mối quan hệ nghiêm túc", "Bạn đời lâu dài"),
            ("Kết hôn", "Bạn đời lâu dài"),
            ("Kết bạn mới thôi 🥰", "Một mối quan hệ nhẹ nhàng, vui vẻ"),
        ]
        
        return (goal1, goal2) in compatible_pairs or (goal2, goal1) in compatible_pairs
    
    def create_conversation(self, user1: User, user2: User, conversation_type: str = "chat") -> Conversation:
        """Tạo cuộc trò chuyện mới giữa 2 người dùng"""
        try:
            # Kiểm tra lại xem cả hai user vẫn đang trong trạng thái searching
            # (để tránh race condition)
            user1_refreshed = self.db.query(User).filter(User.id == user1.id).first()
            user2_refreshed = self.db.query(User).filter(User.id == user2.id).first()
            
            if not user1_refreshed or not user2_refreshed:
                raise ValueError("Không tìm thấy một trong hai user")
            
            if user1_refreshed.state != "searching" or user2_refreshed.state != "searching":
                raise ValueError("Một trong hai user không còn trong trạng thái searching")
            
            # Kiểm tra xem đã có conversation active nào giữa 2 user này chưa
            existing_conversation = self.db.query(Conversation).filter(
                ((Conversation.user1_id == user1.id) & (Conversation.user2_id == user2.id)) |
                ((Conversation.user1_id == user2.id) & (Conversation.user2_id == user1.id)),
                Conversation.is_active == True
            ).first()
            
            if existing_conversation:
                raise ValueError("Đã có conversation active giữa 2 user này")
            
            conversation = Conversation(
                user1_id=user1.id,
                user2_id=user2.id,
                conversation_type=conversation_type,
                is_active=True,
                countdown_start_time=datetime.now(timezone.utc)  # Set thời gian bắt đầu countdown
            )
            
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            
            # Cập nhật trạng thái của cả 2 user
            user1_refreshed.state = "connected"
            user2_refreshed.state = "connected"
            self.db.commit()
            
            return conversation
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def end_conversation(self, conversation: Conversation):
        """Kết thúc cuộc trò chuyện"""
        try:
            conversation.is_active = False
            self.db.commit()
            
            # Cập nhật trạng thái của cả 2 user về waiting
            user1 = self.db.query(User).filter(User.id == conversation.user1_id).first()
            user2 = self.db.query(User).filter(User.id == conversation.user2_id).first()
            
            if user1:
                user1.state = "waiting"
            if user2:
                user2.state = "waiting"
            
            self.db.commit()
            
        except Exception as e:
            print(f"Error ending conversation {conversation.id}: {e}")
            self.db.rollback()
            # Vẫn cố gắng cập nhật trạng thái user ngay cả khi có lỗi
            try:
                user1 = self.db.query(User).filter(User.id == conversation.user1_id).first()
                user2 = self.db.query(User).filter(User.id == conversation.user2_id).first()
                
                if user1:
                    user1.state = "waiting"
                if user2:
                    user2.state = "waiting"
                
                self.db.commit()
            except:
                pass
    
    def cleanup_inactive_conversations(self):
        """Dọn dẹp các cuộc trò chuyện không hoạt động (sau 15 phút)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        inactive_conversations = self.db.query(Conversation).filter(
            Conversation.is_active == True,
            Conversation.last_activity < cutoff_time,
            Conversation.user1_keep == False,
            Conversation.user2_keep == False
        ).all()
        
        for conversation in inactive_conversations:
            self.end_conversation(conversation) 