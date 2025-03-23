import React, { useState, useEffect } from "react";
import { diffWords } from "diff";
import "./BBTView.scss";

const BBTView: React.FC = () => {
  const [expectedResponse, setExpectedResponse] = useState("");
  const [actualResponse, setActualResponse] = useState("");
  const [expectedDiffText, setExpectedDiffText] = useState("");
  const [actualDiffText, setActualDiffText] = useState("");

  // Fetch file content
  const fetchFile = (fileName: string, setFileContent: React.Dispatch<React.SetStateAction<string>>) => {
    fetch(`/xmldata/${fileName}.txt`)
      .then((response) => response.text())
      .then((data) => setFileContent(data))
      .catch((error) => console.error(`Error fetching ${fileName}.txt:`, error));
  };

  // Fetch responses when component loads
  useEffect(() => {
    fetchFile("expectedResponse", setExpectedResponse);
    fetchFile("actualResponse", setActualResponse);
  }, []);

  // Compute the diff and convert to text format
  useEffect(() => {
    if (expectedResponse && actualResponse) {
      const diff = diffWords(expectedResponse, actualResponse);

      let expectedText = "";
      let actualText = "";

      diff.forEach((part) => {
        if (part.removed) {
          expectedText += `<<removed>>${part.value}<</removed>>`; // Mark removed text
        } else {
          expectedText += part.value; // Keep unchanged text
        }

        if (part.added) {
          actualText += `<<added>>${part.value}<</added>>`; // Mark added text
        } else {
          actualText += part.value; // Keep unchanged text
        }
      });

      setExpectedDiffText(expectedText);
      setActualDiffText(actualText);
    }
  }, [expectedResponse, actualResponse]);

  return (
    <div className="bbt-view">
      <h3>Response Comparison</h3>
      <div className="diff-container">
        <div>
          <h4>Expected Response</h4>
          <textarea className="xml-box" readOnly value={expectedDiffText}></textarea>
        </div>
        <div>
          <h4>Actual Response</h4>
          <textarea className="xml-box" readOnly value={actualDiffText}></textarea>
        </div>
      </div>
    </div>
  );
};

export default BBTView;