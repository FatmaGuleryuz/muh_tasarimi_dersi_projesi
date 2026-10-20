import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <div className="pl-64">
        <Outlet />
      </div>
    </div>
  );
}
