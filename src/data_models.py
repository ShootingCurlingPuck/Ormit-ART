from dataclasses import dataclass

from constants import Gender, Program, PromptName


@dataclass
class GuiData:
    gemini_key: str
    applicant_name: str
    assessor_name: str
    gender: Gender
    traineeship: Program
    files: dict[str, str]
    enable_thinking: bool


@dataclass
class IcpGuiData(GuiData):
    icp_info_prompt3: str
    icp_info_prompt6a: str
    icp_info_prompt6b: str


@dataclass
class Prompt:
    name: PromptName
    text: str
    temperature: float = 0.7
