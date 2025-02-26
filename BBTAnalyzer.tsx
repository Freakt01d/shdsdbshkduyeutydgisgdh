import React, { useState } from "react";
import BBTDetailView from "./BBTDetailView";
import "./BBTAnalyzer.css";

interface BBTData {
  id: number;
  workflow: string;
  status: string;
  color: string;
  validated: boolean;
  description?: string;
  comment?: string;
}

const initialRows: BBTData[] = [
  { id: 4198, workflow: "COLLAT", status: "Passed", color: "bg-green-500", validated: false },
  { id: 4199, workflow: "MIFID-1", status: "Passed", color: "bg-green-500", validated: false },
  { id: 4200, workflow: "DFA", status: "False", color: "bg-red-500", validated: false },
  { id: 4201, workflow: "COLLAT", status: "False", color: "bg-red-500", validated: false },
  { id: 4202, workflow: "IFU", status: "Passed", color: "bg-green-500", validated: false },
];

const BBTAnalyzer: React.FC = () => {
  const [showTable, setShowTable] = useState(false);
  const [rows, setRows] = useState<BBTData[]>(initialRows);
  const [selectedData, setSelectedData] = useState<BBTData | null>(null);

  const handleValidate = (index: number) => {
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

  const handleView = (data: BBTData) => {
    setSelectedData(data);
  };

  return (
    <div className="container">
      <div className="controls">
        <select>
          <option>ISO_25.01.31.1</option>
        </select>
        <button onClick={() => setShowTable(true)}>Start Comparison</button>
      </div>

      {showTable && (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Workflow</th>
                <th>Status</th>
                <th>View</th>
                <th>Validate</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.workflow}</td>
                  <td className={row.color}>{row.status}</td>
                  <td>
                    <button onClick={() => handleView(row)}>View</button>
                  </td>
                  <td>
                    <input type="checkbox" checked={row.validated} onChange={() => handleValidate(index)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedData && <BBTDetailView data={selectedData} onClose={() => setSelectedData(null)} />}
    </div>
  );
};

export default BBTAnalyzer;
