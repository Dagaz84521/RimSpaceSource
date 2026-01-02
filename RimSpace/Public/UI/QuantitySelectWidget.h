// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "QuantitySelectWidget.generated.h"

/**
 * 
 */
typedef TFunction<void(int32)> FOnQuantityInputConfirm;

UCLASS()
class RIMSPACE_API UQuantitySelectWidget : public UUserWidget
{
	GENERATED_BODY()
public:
	void Setup(const FText& Title, int32 DefaultQuantity, FOnQuantityInputConfirm InCallBack);

protected:
	virtual void NativeConstruct() override;
	// 标题文本
	UPROPERTY(meta = (BindWidget))
	class UTextBlock* TitleText;

	// 核心组件：输入框
	UPROPERTY(meta = (BindWidget))
	class UEditableTextBox* InputBox;

	// 确认按钮
	UPROPERTY(meta = (BindWidget))
	class UButton* ConfirmButton;

	// 取消按钮
	UPROPERTY(meta = (BindWidget))
	class UButton* CancelButton;

private:
	FOnQuantityInputConfirm OnConfirm;

	UFUNCTION()
	void OnConfirmClicked();

	UFUNCTION()
	void OnCancelClicked();
	
	// 当文本改变时，用于过滤非数字字符（可选）
	UFUNCTION()
	void OnInputTextChanged(const FText& Text);
	
};
