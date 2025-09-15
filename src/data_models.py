from typing import TypedDict

from constants import Gender, Program


class GuiData(TypedDict):
    gemini_key: str
    applicant_name: str
    assessor_name: str
    gender: Gender
    traineeship: Program
    files: dict[str, str]
    enable_thinking: bool


class IcpGuiData(GuiData):
    icp_info_prompt3: str
    icp_info_prompt6a: str
    icp_info_prompt6b: str
