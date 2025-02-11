import React, { useState } from "react";

// Define the row type
interface Row {
  id: number;
  workflow: string;
  status: string;
  color: string;
  validated: boolean;
}

const BBTAnalyzer: React.FC = () => {
  const initialRows: Row[] = [
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
  const [rows, setRows] = useState<Row[]>(initialRows);

  const handleValidate = (index: number) => {
    setRows((prevRows) =>
      prevRows.map((row, i) =>
        i === index
          ? {
              ...row,
              validated: !row.validated,
              status: !row.validated ? "Validated" : initialRows.find((r) => r.id === row.id)?.status || "Passed",
              color: !row.validated ? "bg-yellow-500" : initialRows.find((r) => r.id === row.id)?.color || "bg-green-500",
            }
          : row
      )
    );
  };

  const totalCount = rows.length;
  const validatedCount = rows.filter((row) => row.validated).length;
  const passedCount = rows.filter((row) => row.status === "Passed" || (row.status === "Validated" && initialRows.find((r) => r.id === row.id)?.status === "Passed")).length;
  const failedCount = rows.filter((row) => row.status === "False" || (row.status === "Validated" && initialRows.find((r) => r.id === row.id)?.status === "False")).length;

  return (
    <div className="p-4 bg-gray-100 min-h-screen">
      <div className="flex items-center space-x-2 mb-4">
        <select className="border p-2 rounded">
          <option>ISO_25.01.31.1</option>
        </select>
        <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={() => setShowTable(true)}>
          Start Comparison
        </button>
      </div>

      {showTable && (
        <div className="bg-white p-4 rounded shadow-md overflow-auto">
          <table className="w-full border-collapse border text-left">
            <thead>
              <tr className="bg-gray-200">
                <th className="border p-2">ID</th>
                <th className="border p-2">Workflow</th>
                <th className="border p-2">Is Active</th>
                <th className="border p-2">Status</th>
                <th className="border p-2">Validate</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id} className="border">
                  <td className="border p-2">{row.id}</td>
                  <td className="border p-2">{row.workflow}</td>
                  <td className="border p-2">
                    <input type="checkbox" checked readOnly />
                  </td>
                  <td className={`border p-2 text-white ${row.color}`}>{row.status}</td>
                  <td className="border p-2">
                    <input type="checkbox" checked={row.validated} onChange={() => handleValidate(index)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex justify-between">
        <div className="w-1/4 bg-white p-4 rounded shadow-md">
          <h3 className="font-bold">Statistics</h3>
          <p>Total Count: {totalCount}</p>
          <p>Passed Count: {passedCount}</p>
          <p>Failed Count: {failedCount}</p>
          <p>Validated Count: {validatedCount}</p>
        </div>
      </div>
    </div>
  );
};

export default BBTAnalyzer;