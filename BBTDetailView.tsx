import { diffWords } from "diff";

useEffect(() => {
  if (ExpectedResponse && ActualResponse) {
    const diff = diffWords(ExpectedResponse, ActualResponse);

    let expectedText = "";
    let actualText = "";
    let lastRemoved = ""; // Track removed text to match with added parts

    diff.forEach((part) => {
      if (part.removed) {
        lastRemoved = part.value;
        expectedText += `<span class="removed">${part.value}</span>`;
      } else if (part.added) {
        if (lastRemoved) {
          expectedText = expectedText.replace(
            `<span class="removed">${lastRemoved}</span>`,
            `<span class="changed">${lastRemoved}</span>`
          );
          actualText += `<span class="changed">${part.value}</span>`;
          lastRemoved = "";
        } else {
          actualText += `<span class="added">${part.value}</span>`;
        }
      } else {
        expectedText += part.value;
        actualText += part.value;
        lastRemoved = "";
      }
    });

    setExpectedDiffText(expectedText);
    setActualDiffText(actualText);
  }
}, [ExpectedResponse, ActualResponse]);