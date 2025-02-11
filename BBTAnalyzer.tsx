// BBTAnalyzer.jsx
import React, { useState } from "react";
import "./BBTAnalyzer.css";

const BBTAnalyzer = () => {
  const initialRows = [
    { id: 4198, workflow: "COLLAT", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4199, workflow: "MIFID-1", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4200, workflow: "DFA", status: "False", color: "bg-red-500", validated: false },
    { id: 4201, workflow: "COLLAT", status: "False", color: "bg-red-500", validated: false },
    { id: 4202, workflow: "IFU", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4203, workflow: "DFA", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4204, workflow: "FATCA_ETNC", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4205, workflow: "DFA", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4206, workflow: "COLLAT", status: "Passed", color: "bg-green-500", validated: false },
    { id: 4207, workflow: "MIFID-1", status: "Passed", color: "bg-green-500", validated: false },
  ];

  const [showTable, setShowTable] = useState(false);
  const [rows, setRows] = useState(initialRows);

  const handleValidate = (index) => {
    setRows((prevRows) =>
      prevRows.map((row, i) =>
        i === index
          ? {
              ...row,
              validated: !row.validated,
              status: !row.validated ? "Validated" : initialRows.find(r => r.id === row.id)?.status || "Passed",
              color: !row.validated ? "bg-yellow-500" : (initialRows.find(r => r.id === row.id)?.color || "bg-green-500"),
            }
          : row
      )
    );
  };

  const totalCount = rows.length;
  const validatedCount = rows.filter(row => row.validated).length;
  const passedCount = rows.filter(row => row.status === "Passed" || row.status === "Validated" && initialRows.find(r => r.id === row.id)?.status === "Passed").length;
  const failedCount = rows.filter(row => row.status === "False" || row.status === "Validated" && initialRows.find(r => r.id === row.id)?.status === "False").length;

  return (
    <div className="container">
      <div className="controls">
        <select>
          <option>ISO_25.01.31.1</option>
        </select>
        <button onClick={() => setShowTable(true)}>Start Comparison</button>
        <button className="gray">View Report</button>
        <button className="gray">Email Report</button>
        <div className="spacer"></div>
        <button className="gray">Initiate New BBT</button>
        <button className="gray">Add BBT</button>
      </div>

      {showTable && (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Workflow</th>
                <th>Is Active</th>
                <th>Status</th>
                <th>View</th>
                <th>Validate</th>
                <th>Description</th>
                <th>Comment</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.workflow}</td>
                  <td><input type="checkbox" checked readOnly /></td>
                  <td className={row.color}>{row.status}</td>
                  <td><button>View</button></td>
                  <td>
                    <input type="checkbox" checked={row.validated} onChange={() => handleValidate(index)} />
                  </td>
                  <td>Description here</td>
                  <td>Comment here</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="stats">
        <div className="filter">
          <h3>Filter</h3>
          <label><input type="checkbox" /> Passed</label><br/>
          <label><input type="checkbox" /> Failed</label><br/>
          <label><input type="checkbox" /> Validated</label>
        </div>

        <div className="statistics">
          <h3>Statistics</h3>
          <p>Total Count: {totalCount}</p>
          <p>Passed Count: {passedCount}</p>
          <p>Failed Count: {failedCount}</p>
          <p>Validated Count: {validatedCount}</p>
          <p>Executed on: 1/31/2025 9:43 AM</p>
          <button>Update Active Flag to DB</button>
          <button className="gray">Save and Export Report</button>
        </div>
      </div>
    </div>
  );
};

export default BBTAnalyzer;
