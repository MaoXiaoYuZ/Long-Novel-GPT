from typing import List
from pydantic import BaseModel


class ChapterModel(BaseModel):
    chapter1_title: str
    chapter1_content: str
    chapter2_title: str
    chapter2_content: str
    chapter3_title: str
    chapter3_content: str
    chapter4_title: str
    chapter4_content: str
    chapter5_title: str
    chapter5_content: str
    chapter6_title: str
    chapter6_content: str
    chapter7_title: str
    chapter7_content: str
    chapter8_title: str
    chapter8_content: str
    chapter9_title: str
    chapter9_content: str
    chapter10_title: str
    chapter10_content: str
    chapter11_title: str
    chapter11_content: str
    chapter12_title: str
    chapter12_content: str


class CharacterModel(BaseModel):
    name_1: str
    personality_1: str
    appearance_1: str
    relationship_1: str
    appearance_1: str
    inner_outer_conflict_1: str
    appearance_chapter_1: str
    name_2: str
    personality_2: str
    appearance_2: str
    relationship_2: str
    appearance_2: str
    inner_outer_conflict_2: str
    appearance_chapter_2: str
    name_3: str
    personality_3: str
    appearance_3: str
    relationship_3: str
    appearance_3: str
    inner_outer_conflict_3: str
    appearance_chapter_3: str
    name_4: str
    personality_4: str
    appearance_4: str
    relationship_4: str
    appearance_4: str
    inner_outer_conflict_4: str
    appearance_chapter_4: str
    name_5: str
    personality_5: str
    appearance_5: str
    relationship_5: str
    appearance_5: str
    inner_outer_conflict_5: str
    appearance_chapter_5: str
    name_6: str
    personality_6: str
    appearance_6: str
    relationship_6: str
    appearance_6: str
    inner_outer_conflict_6: str
    appearance_chapter_6: str
    name_7: str
    personality_7: str
    appearance_7: str
    relationship_7: str
    appearance_7: str
    inner_outer_conflict_7: str
    appearance_chapter_7: str
    name_8: str
    personality_8: str
    appearance_8: str
    relationship_8: str
    appearance_8: str
    inner_outer_conflict_8: str
    appearance_chapter_8: str
    name_9: str
    personality_9: str
    appearance_9: str
    relationship_9: str
    appearance_9: str
    inner_outer_conflict_9: str
    appearance_chapter_9: str
    name_10: str
    personality_10: str
    appearance_10: str
    relationship_10: str
    appearance_10: str
    inner_outer_conflict_10: str
    appearance_chapter_10: str
    name_11: str
    personality_11: str
    appearance_11: str
    relationship_11: str
    appearance_11: str
    inner_outer_conflict_11: str
    appearance_chapter_11: str
    name_12: str
    personality_12: str
    appearance_12: str
    relationship_12: str
    appearance_12: str
    inner_outer_conflict_12: str
    appearance_chapter_12: str


class RelationshipModel(BaseModel):
    source_1: str  # 关系源头角色
    target_1: str  # 关系目标角色 
    closeness_1: float  # 亲密度 0-1
    relationship_type_1: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_1: str  # 关系说明

    source_2: str  # 关系源头角色
    target_2: str  # 关系目标角色 
    closeness_2: float  # 亲密度 0-1
    relationship_type_2: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_2: str  # 关系说明

    source_3: str  # 关系源头角色
    target_3: str  # 关系目标角色 
    closeness_3: float  # 亲密度 0-1
    relationship_type_3: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_3: str  # 关系说明

    source_4: str  # 关系源头角色
    target_4: str  # 关系目标角色 
    closeness_4: float  # 亲密度 0-1
    relationship_type_4: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_4: str  # 关系说明

    source_5: str  # 关系源头角色
    target_5: str  # 关系目标角色 
    closeness_5: float  # 亲密度 0-1
    relationship_type_5: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_5: str  # 关系说明

    source_6: str  # 关系源头角色
    target_6: str  # 关系目标角色 
    closeness_6: float  # 亲密度 0-1
    relationship_type_6: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_6: str  # 关系说明

    source_7: str  # 关系源头角色
    target_7: str  # 关系目标角色 
    closeness_7: float  # 亲密度 0-1
    relationship_type_7: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_7: str  # 关系说明

    source_8: str  # 关系源头角色
    target_8: str  # 关系目标角色 
    closeness_8: float  # 亲密度 0-1
    relationship_type_8: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_8: str  # 关系说明

    source_9: str  # 关系源头角色
    target_9: str  # 关系目标角色 
    closeness_9: float  # 亲密度 0-1
    relationship_type_9: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_9: str  # 关系说明

    source_10: str  # 关系源头角色
    target_10: str  # 关系目标角色 
    closeness_10: float  # 亲密度 0-1
    relationship_type_10: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_10: str  # 关系说明

    source_11: str  # 关系源头角色
    target_11: str  # 关系目标角色 
    closeness_11: float  # 亲密度 0-1
    relationship_type_11: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_11: str  # 关系说明

    source_12: str  # 关系源头角色
    target_12: str  # 关系目标角色 
    closeness_12: float  # 亲密度 0-1
    relationship_type_12: str  # 关系类型 (mentor/colleague/friend/antagonist)
    explanation_12: str  # 关系说明

class CharacterRelationshipMap(BaseModel):
    name_1: str
    gender_1: str
    importance_1: int
    alignment_1: str
    role_type_1: str
    inner_outer_conflict_1: str
    personality_1: str

    name_2: str
    gender_2: str
    importance_2: int
    alignment_2: str
    role_type_2: str
    inner_outer_conflict_2: str
    personality_2: str

    name_3: str
    gender_3: str
    importance_3: int
    alignment_3: str
    role_type_3: str
    inner_outer_conflict_3: str
    personality_3: str

    name_4: str
    gender_4: str
    importance_4: int
    alignment_4: str
    role_type_4: str
    inner_outer_conflict_4: str
    personality_4: str

    name_5: str
    gender_5: str
    importance_5: int
    alignment_5: str
    role_type_5: str
    inner_outer_conflict_5: str
    personality_5: str

    name_6: str
    gender_6: str
    importance_6: int
    alignment_6: str
    role_type_6: str
    inner_outer_conflict_6: str
    personality_6: str

    name_7: str
    gender_7: str
    importance_7: int
    alignment_7: str
    role_type_7: str
    inner_outer_conflict_7: str
    personality_7: str

    name_8: str
    gender_8: str
    importance_8: int
    alignment_8: str
    role_type_8: str
    inner_outer_conflict_8: str
    personality_8: str

    name_9: str
    gender_9: str
    importance_9: int
    alignment_9: str
    role_type_9: str
    inner_outer_conflict_9: str
    personality_9: str

    name_10: str
    gender_10: str
    importance_10: int
    alignment_10: str
    role_type_10: str
    inner_outer_conflict_10: str
    personality_10: str

    name_11: str
    gender_11: str
    importance_11: int
    alignment_11: str
    role_type_11: str
    inner_outer_conflict_11: str
    personality_11: str

    name_12: str
    gender_12: str
    importance_12: int
    alignment_12: str
    role_type_12: str
    inner_outer_conflict_12: str
    personality_12: str