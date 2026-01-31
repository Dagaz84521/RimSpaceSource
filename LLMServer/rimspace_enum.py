from enum import Enum

class EInteractionType(Enum):
    NONE = "EInteractionType::EAT_None"
    WorkStation = "EInteractionType::EAT_WorkStation"
    CultivateChamber = "EInteractionType::EAT_CultivateChamber"
    Bed = "EInteractionType::EAT_Bed"
    Stove = "EInteractionType::EAT_Stove"
    Table = "EInteractionType::EAT_Table"
    Storage = "EInteractionType::EAT_Storage"

class ECultivatePhase(Enum):
    NONE = "ECultivatePhase::ECP_None"
    WaitingToPlant = "ECultivatePhase::ECP_WaitingToPlant"
    Planting = "ECultivatePhase::ECP_Planting"
    Growing = "ECultivatePhase::ECP_Growing"
    ReadyToHarvest = "ECultivatePhase::ECP_ReadyToHarvest"
    Harvesting = "ECultivatePhase::ECP_Harvesting"

class ECultivateType(Enum):
    NONE = "ECultivateType::ECT_None"
    Corn = "ECultivateType::ECT_Corn"
    Cotton = "ECultivateType::ECT_Cotton"
