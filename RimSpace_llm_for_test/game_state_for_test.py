game_state =  {
        "Environment": {
            "Actors": [
                {
                    "ActorName": "CultivateChamber_1",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Cotton",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "CultivateChamber_2",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Cotton",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "CultivateChamber_3",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Corn",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "CultivateChamber_4",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Corn",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "WorkStation",
                    "ActorType": "EInteractionType::EAT_WorkStation",
                    "Inventory": {
                    },
                    "TaskList": {
                        "3001": 3,
                    },
                },
                {
                    "ActorName": "Stove",
                    "ActorType": "EInteractionType::EAT_Stove",
                    "Inventory": {},
                },
                {
                    "ActorName": "Storage",
                    "ActorType": "EInteractionType::EAT_Storage",
                    "Inventory": {
                        "1001": 5, # Cotton
                        "1002": 3, # Corn
                    },
                },
                {
                    "ActorName": "Table",
                    "ActorType": "EInteractionType::EAT_Table",
                },
                {
                    "ActorName": "Bed_1",
                    "ActorType": "EInteractionType::EAT_Bed",
                },
                {
                    "ActorName": "Bed_2",
                    "ActorType": "EInteractionType::EAT_Bed",
                },
                {
                    "ActorName": "Bed_3",
                    "ActorType": "EInteractionType::EAT_Bed",
                },
            ]
        },
        "Characters": {
            "Characters": [
                {
                    "CharacterName": "Farmer",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Thinking",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 99.75,
                        "MaxHunger": 100.0,
                        "Energy": 99.75,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanFarm"],
                },
                {
                    "CharacterName": "Crafter",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Waiting",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 99.8,
                        "MaxHunger": 100.0,
                        "Energy": 99.8,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanCraft"],
                },
                {
                    "CharacterName": "Chef",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Waiting",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 99.8,
                        "MaxHunger": 100.0,
                        "Energy": 99.8,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanCook"],
                },
            ]
        },
    }