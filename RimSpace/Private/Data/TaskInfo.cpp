// Fill out your copyright notice in the Description page of Project Settings.


#include "Data/TaskInfo.h"

FTask* UTaskInfo::GetTask(int32 TaskID)
{
	return Tasks.FindByPredicate([TaskID](const FTask& Task)
	{
		return Task.TaskID == TaskID;
	});
}
