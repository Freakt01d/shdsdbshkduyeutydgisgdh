import React, { useState, useEffect } from "react";

const BBTView: React.FC = () => {
  const [file1, setFile1] = useState("");
  const [file2, setFile2] = useState("");
  const [file3, setFile3] = useState("");
  const [file4, setFile4] = useState("");
  const [file5, setFile5] = useState("");

  // Function to fetch and set text for a given file
  const fetchFile = (fileName: string, setFileContent: React.Dispatch<React.SetStateAction<string>>) => {
    fetch(`/xml/${fileName}.txt`)
      .then((response) => response.text())
      .then((data) => setFileContent(data))
      .catch((error) => console.error(`Error fetching ${fileName}.txt:`, error));
  };

  useEffect(() => {
    fetchFile("file1", setFile1);
    fetchFile("file2", setFile2);
    fetchFile("file3", setFile3);
    fetchFile("file4", setFile4);
    fetchFile("file5", setFile5);
  }, []);

  return (
    <div className="bbt-view">
      <textarea className="xml-box" readOnly value={file1} />
      <textarea className="xml-box" readOnly value={file2} />
      <textarea className="xml-box" readOnly value={file3} />
      <textarea className="xml-box" readOnly value={file4} />
      <textarea className="xml-box" readOnly value={file5} />
    </div>
  );
};

export default BBTView;