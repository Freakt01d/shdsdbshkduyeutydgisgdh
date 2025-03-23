import { diffWords } from "diff";

useEffect(() => {
  if (ExpectedResponse && ActualResponse) {
    const diff = diffWords(ExpectedResponse, ActualResponse);

    const expectedText = diff.map((part, index) => {
      if (part.removed) return <span key={index} style={{ backgroundColor: "red" }}>{part.value}</span>;
      if (part.added) return <span key={index} style={{ backgroundColor: "yellow" }}>{part.value}</span>;
      return <span key={index}>{part.value}</span>;
    });

    const actualText = diff.map((part, index) => {
      if (part.removed) return <span key={index} style={{ backgroundColor: "red" }}>{part.value}</span>;
      if (part.added) return <span key={index} style={{ backgroundColor: "yellow" }}>{part.value}</span>;
      return <span key={index}>{part.value}</span>;
    });

    setExpectedDiffText(expectedText);
    setActualDiffText(actualText);
  }
}, [ExpectedResponse, ActualResponse]);