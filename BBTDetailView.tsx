const processDiff = (diff: any) => {
  let expectedText: JSX.Element[] = [];
  let actualText: JSX.Element[] = [];

  let i = 0;
  while (i < diff.length) {
    const part = diff[i];

    // If a removal is followed by an addition, it's a change (modified).
    if (part.removed && i + 1 < diff.length && diff[i + 1].added) {
      expectedText.push(<span key={`exp-${i}`} className="changed">{part.value}</span>);
      actualText.push(<span key={`act-${i}`} className="changed">{diff[i + 1].value}</span>);
      i += 2; // Skip next part since it's already handled
      continue;
    }

    if (part.removed) {
      // Removed text should appear only in expected (Red)
      expectedText.push(<span key={`exp-${i}`} className="removed">{part.value}</span>);
    } 
    else if (part.added) {
      // Added text should appear only in actual (Yellow)
      actualText.push(<span key={`act-${i}`} className="added">{part.value}</span>);
    } 
    else {
      // Unchanged text should appear in both
      expectedText.push(<span key={`exp-${i}`}>{part.value}</span>);
      actualText.push(<span key={`act-${i}`}>{part.value}</span>);
    }

    i++;
  }

  return { expectedText, actualText };
};