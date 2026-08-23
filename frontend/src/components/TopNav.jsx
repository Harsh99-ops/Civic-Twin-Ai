import { useState, useRef, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { Layers, Radio, ChevronDown, User, Building2, Check } from "lucide-react";
import "./TopNav.css";

export default function TopNav({ role, onRoleChange, backendUp }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function onClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <header className="topnav">
      <div className="topnav__brand">
        <div className="topnav__logo">
          <Layers size={18} strokeWidth={2.4} />
        </div>
        <div>
          <div className="topnav__title">CIVIC-TWIN AI</div>
          <div className="topnav__subtitle">Digital Infrastructure Platform</div>
        </div>
      </div>

      <nav className="topnav__links">
        <NavLink to="/report" className={({ isActive }) => (isActive ? "active" : "")}>
          Report Issue
        </NavLink>
        <NavLink to="/map" className={({ isActive }) => (isActive ? "active" : "")}>
          GIS Map
        </NavLink>
        {role === "admin" && (
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : "")}>
            Priority Engine
          </NavLink>
        )}
      </nav>

      <div className="topnav__right">
        <div className={`topnav__live ${backendUp ? "" : "topnav__live--down"}`}>
          <Radio size={13} />
          {backendUp ? "LIVE" : "OFFLINE"}
        </div>

        <div className="topnav__roleswitch" ref={menuRef}>
          <button className="topnav__rolebtn" onClick={() => setMenuOpen((v) => !v)}>
            {role === "admin" ? <Building2 size={15} /> : <User size={15} />}
            <span>{role === "admin" ? "Municipal / PWD" : "Citizen"}</span>
            <ChevronDown size={14} />
          </button>

          {menuOpen && (
            <div className="topnav__menu">
              <div className="topnav__menu-label">Switch role</div>
              <button
                className="topnav__menu-item"
                onClick={() => {
                  onRoleChange("citizen");
                  setMenuOpen(false);
                }}
              >
                <User size={15} />
                <span>Citizen</span>
                {role === "citizen" && <Check size={14} className="topnav__check" />}
              </button>
              <button
                className="topnav__menu-item"
                onClick={() => {
                  onRoleChange("admin");
                  setMenuOpen(false);
                }}
              >
                <Building2 size={15} />
                <span>Municipal / PWD Admin</span>
                {role === "admin" && <Check size={14} className="topnav__check" />}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
