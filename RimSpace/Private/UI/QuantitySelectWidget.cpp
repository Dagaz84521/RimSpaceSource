#include "UI/QuantitySelectWidget.h"
#include "Components/TextBlock.h"
#include "Components/EditableTextBox.h"
#include "Components/Button.h"

void UQuantitySelectWidget::Setup(const FText& Title, int32 DefaultValue, FOnQuantityInputConfirm InCallback)
{
	if (TitleText)
	{
		TitleText->SetText(Title);
	}
	if (InputBox)
	{
		// 设置默认值，如果不需要默认值可以设为空
		InputBox->SetText(DefaultValue > 0 ? FText::AsNumber(DefaultValue) : FText::GetEmpty());
	}
	OnConfirm = InCallback;
}

void UQuantitySelectWidget::NativeConstruct()
{
	Super::NativeConstruct();

	if (ConfirmButton)
		ConfirmButton->OnClicked.AddDynamic(this, &UQuantitySelectWidget::OnConfirmClicked);
	
	if (CancelButton)
		CancelButton->OnClicked.AddDynamic(this, &UQuantitySelectWidget::OnCancelClicked);

	if (InputBox)
		InputBox->OnTextChanged.AddDynamic(this, &UQuantitySelectWidget::OnInputTextChanged);
}

void UQuantitySelectWidget::OnInputTextChanged(const FText& Text)
{
	// 简单的输入过滤：如果包含非数字，强制去除非数字部分（体验优化）
	if (!Text.IsNumeric())
	{
		FString Str = Text.ToString();
		FString NumericStr = "";
		for (TCHAR Char : Str)
		{
			if (FChar::IsDigit(Char))
			{
				NumericStr.AppendChar(Char);
			}
		}
		if (InputBox)
		{
			InputBox->SetText(FText::FromString(NumericStr));
		}
	}
}

void UQuantitySelectWidget::OnConfirmClicked()
{
	if (InputBox)
	{
		FString InputStr = InputBox->GetText().ToString();
		if (InputStr.IsNumeric())
		{
			int32 Value = FCString::Atoi(*InputStr);
			
			// 执行回调，把数字传回给 WorkStation
			if (OnConfirm)
			{
				OnConfirm(Value);
			}
		}
	}
	// 关闭 UI (这部分逻辑也可以放在 PlayerController 里处理)
	RemoveFromParent();
}

void UQuantitySelectWidget::OnCancelClicked()
{
	// 直接关闭，不执行回调
	RemoveFromParent();
}