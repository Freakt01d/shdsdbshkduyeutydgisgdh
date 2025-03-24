const processDiff = (diff: any) => {
  let expectedText = [];
  let actualText = [];

  diff.forEach((part: { added?: boolean; removed?: boolean; value: string }, index: number, arr: any[]) => {
    if (part.removed && arr[index + 1]?.added) {
      // Case: Modified (Appears Green in Both)
      expectedText.push(<span key={index} className="changed">{part.value}</span>);
      actualText.push(<span key={index} className="changed">{arr[index + 1].value}</span>);
    } else if (part.removed) {
      // Case: Removed (Appears in Expected Only - Red)
      expectedText.push(<span key={index} className="removed">{part.value}</span>);
    } else if (part.added) {
      // Case: Added (Appears in Actual Only - Yellow)
      actualText.push(<span key={index} className="added">{part.value}</span>);
    } else {
      // Case: Unchanged (Appears in Both)
      expectedText.push(<span key={index}>{part.value}</span>);
      actualText.push(<span key={index}>{part.value}</span>);
    }
  });

  return { expectedText, actualText };
};

useEffect(() => {
  if (ExpectedResponse && ActualResponse) {
    const diff = diffWords(ExpectedResponse, ActualResponse);
    const { expectedText, actualText } = processDiff(diff);
    setExpectedDiffText(expectedText);
    setActualDiffText(actualText);
  }
}, [ExpectedResponse, ActualResponse]);