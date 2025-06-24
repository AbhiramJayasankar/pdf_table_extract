from contextgem import JsonObjectConcept
from typing import Union, List

planned_machinery_survey_concept = JsonObjectConcept(
    name="Planned_Machinery_Survey_Schema",
    llm_role="extractor_vision",
    # llm_role="reasoner_vision",
    description="""IMPORTANT: You will receive MULTIPLE pages from the 'NK-SHIPS: Survey Status - Planned Machinery Survey' report.

    PAGE HANDLING INSTRUCTIONS:
    - Page 1 : Contains column headers AND data rows. Use it as reference for column positions AND extract its data.
    - Pages 2 onwards: Continue extracting data using the column positions identified from Page 1.
    
    EXTRACTION TASK:
    1. From Page 1: Identify the column headers and their exact positions
    2. Extract ALL survey items from Page 1 (excluding the header row)
    3. Apply the same column positions to ALL subsequent pages to correctly map the data
    4. Extract survey items from ALL pages (including Page 1)
    5. Combine all extracted items into a single comprehensive list
    
    The data should be organized by machinery system (e.g., Main Diesel Engine, Shafting & Auxiliary Engine), with each system containing its corresponding survey items in row-wise format. Survey items from all pages should be merged into their respective system categories.""",
    add_justifications=False,
    add_references=False,
    singular_occurrence=False,
    justification_depth="brief",
    justification_max_sents=2,
    structure={
        # "report_header": {
        #     "report_title": Union[int, float, str, None],
        #     "name_of_ship": Union[int, float, str, None],
        #     "class_no": Union[int, float, str, None],
        #     "imo_no": Union[int, float, str, None],
        # },
        "machinery_systems": [
            {
                "system_applied": Union[int, float, str, None],
                "survey_items": [
                    {
                        "code": Union[int, float, str, None],
                        "survey_item_description": Union[int, float, str, None],
                        "system": Union[int, float, str, None],
                        "ap": Union[int, float, str, None],
                        "status": Union[int, float, str, None],
                        "last_date": Union[int, float, str, None],
                        "ex": Union[int, float, str, None],
                        "next_date": Union[int, float, str, None],
                        "exam_by_ce": Union[int, float, str, None],
                        "postponed": Union[int, float, str, None],
                    }
                ]
            }
        ],
        # "legend": {
        #     "system_applied_explanation": Union[int, float, str, None],
        #     "system_explanation": Union[int, float, str, None],
        #     "ap_explanation": Union[int, float, str, None],
        #     "kind_of_examination_explanation": Union[int, float, str, None],
        #     "confirmatory_survey_explanation": Union[int, float, str, None],
        #     "ex_by_ce_explanation": Union[int, float, str, None],
        # }
    },
)