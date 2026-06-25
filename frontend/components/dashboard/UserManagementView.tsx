"use client";

import { useEffect, useState } from "react";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { useStore } from "../../app/store";
import { Users, UserPlus, ShieldAlert, Key, Mail, User, Shield, RefreshCw, X } from "lucide-react";

export default function UserManagementView() {
  const { addToast } = useToast();
  const currentUser = useStore((state) => state.user);

  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Registration Form States
  const [emailInput, setEmailInput] = useState("");
  const [usernameInput, setUsernameInput] = useState("");
  const [fullNameInput, setFullNameInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [roleInput, setRoleInput] = useState("analyst");
  const [registering, setRegistering] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const list = await api.getUsers();
      setUsers(list || []);
    } catch (err: any) {
      addToast(err.message || "Failed to fetch user list", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser.role === "admin") {
      fetchUsers();
    }
  }, [currentUser]);

  const handleRegisterUser = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validations
    if (!emailInput.includes("@")) {
      addToast("Please enter a valid email address.", "error");
      return;
    }
    if (usernameInput.length < 3) {
      addToast("Username must be at least 3 characters long.", "error");
      return;
    }
    if (fullNameInput.length < 2) {
      addToast("Full name must be at least 2 characters long.", "error");
      return;
    }
    if (passwordInput.length < 6) {
      addToast("Password must be at least 6 characters long.", "error");
      return;
    }

    setRegistering(true);
    try {
      await api.register({
        email: emailInput,
        username: usernameInput.toLowerCase().trim(),
        full_name: fullNameInput.trim(),
        password: passwordInput,
        role: roleInput
      });

      addToast(`User ${usernameInput} registered successfully as ${roleInput}.`, "success");

      // Clear fields
      setEmailInput("");
      setUsernameInput("");
      setFullNameInput("");
      setPasswordInput("");
      setRoleInput("analyst");

      // Refresh list
      fetchUsers();
      setShowModal(false);
    } catch (err: any) {
      addToast(err.message || "Registration failed.", "error");
    } finally {
      setRegistering(false);
    }
  };

  if (currentUser.role !== "admin") {
    return (
      <div className="bg-[#09090B] border border-[#27272A] rounded-xl p-8 text-center space-y-4 text-zinc-100 font-sans shadow-2xl max-w-md mx-auto">
        <div className="h-12 w-12 rounded bg-red-950/40 border border-red-900/50 flex items-center justify-center mx-auto text-[#DC2626]">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white font-mono uppercase tracking-wider">GATED ACCESS ONLY</h2>
          <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
            Your current account role <code className="bg-[#18181B] text-zinc-300 px-1 py-0.5 rounded border border-[#27272A]">{currentUser.role}</code> does not have authorization clearance to access the User Directory Management view.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#09090B] border border-[#27272A] rounded-xl p-8 text-zinc-100 font-sans shadow-2xl space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[#27272A] pb-6">
        <div>
          <h2 className="text-xl font-mono font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="h-5 w-5 text-[#DC2626]" /> USER DIRECTORY MANAGEMENT
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Register new platform accounts, assign functional roles, and view user directory.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowModal(true)}
            className="px-3 py-2 border border-[#27272A] rounded bg-[#DC2626] hover:bg-[#B91C1C] text-white font-mono text-xs uppercase font-bold tracking-wider cursor-pointer transition-colors flex items-center gap-1.5"
          >
            <UserPlus className="h-4 w-4" /> Provision Account
          </button>
          <button
            onClick={fetchUsers}
            disabled={loading}
            className="p-2 border border-[#27272A] rounded bg-[#18181B] text-zinc-400 hover:text-white transition-all cursor-pointer disabled:opacity-50"
            title="Refresh User List"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="space-y-4">
        <h3 className="text-xs font-mono font-bold tracking-widest text-[#DC2626] uppercase">Active Accounts Directory</h3>
        {loading && users.length === 0 ? (
          <div className="bg-[#18181B] border border-[#27272A] p-8 rounded-lg text-center text-xs text-zinc-500 font-mono">
            Fetching active directory records...
          </div>
        ) : (
          <div className="bg-[#18181B] border border-[#27272A] rounded-lg overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse hardware-table">
                <thead>
                  <tr className="bg-[#09090B] border-b border-[#27272A] text-zinc-400 font-mono text-[10px] uppercase">
                    <th className="p-4 font-bold">Username</th>
                    <th className="p-4 font-bold">Email</th>
                    <th className="p-4 font-bold">Assigned Role</th>
                    <th className="p-4 font-bold text-center">Security Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#27272A] font-sans">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-[#09090B] transition-colors">
                      <td className="p-4 font-bold text-white flex items-center gap-2">
                        <div className="h-5 w-5 rounded-full bg-[#09090B] border border-[#27272A] flex items-center justify-center font-mono text-[10px] text-zinc-300 font-bold uppercase">
                          {u.username.charAt(0)}
                        </div>
                        <span>{u.username}</span>
                      </td>
                      <td className="p-4 text-zinc-400 font-mono">{u.email}</td>
                      <td className="p-4 text-zinc-300 font-mono text-[10px]">
                        <span className={`px-2 py-0.5 rounded border ${
                          u.role === "admin"
                            ? "bg-purple-950/30 text-purple-400 border-purple-900/50"
                            : u.role === "director"
                            ? "bg-blue-950/30 text-blue-400 border-blue-900/50"
                            : u.role === "manager"
                            ? "bg-amber-950/30 text-amber-400 border-amber-900/50"
                            : "bg-zinc-800 text-zinc-400 border-zinc-700/50"
                        }`}>
                          {u.role.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-4 text-center">
                        <span className={`inline-block h-2 w-2 rounded-full ${
                          u.is_active ? "bg-green-500 animate-pulse-slow" : "bg-zinc-650"
                        }`} />
                        <span className="text-[10px] text-zinc-450 ml-1.5 font-mono capitalize">
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Provision Account Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-md bg-[#18181B] border border-[#27272A] rounded-xl p-6 space-y-6 shadow-2xl relative">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-white cursor-pointer transition-colors"
              aria-label="Close provision modal"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="space-y-1 text-left">
              <h3 className="text-sm font-mono font-bold tracking-widest text-[#DC2626] uppercase flex items-center gap-2">
                <UserPlus className="h-4 w-4" /> Provision Account
              </h3>
              <p className="text-[10px] text-zinc-400 font-mono">Create new credentials and assign functional roles.</p>
            </div>

            <form onSubmit={handleRegisterUser} className="space-y-4 text-left">
              <div className="space-y-1">
                <label className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider block">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="email"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#DC2626]"
                    placeholder="name@enterprise.com"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider block">Username</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="text"
                    value={usernameInput}
                    onChange={(e) => setUsernameInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#DC2626]"
                    placeholder="e.g. jsmith"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider block">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="text"
                    value={fullNameInput}
                    onChange={(e) => setFullNameInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#DC2626]"
                    placeholder="e.g. Jane Smith"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider block">Password</label>
                <div className="relative">
                  <Key className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="password"
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#DC2626]"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider block">Platform Role</label>
                <div className="relative">
                  <Shield className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <select
                    value={roleInput}
                    onChange={(e) => setRoleInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-xs text-white focus:outline-none focus:border-[#DC2626]"
                  >
                    <option value="analyst">Analyst (View & Create PO Drafts)</option>
                    <option value="manager">Manager (Approve PO &lt; ₹100,000)</option>
                    <option value="director">Director (Approve PO &lt; ₹500,000)</option>
                    <option value="admin">Administrator (Full Access)</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={registering}
                className="w-full py-2.5 bg-[#DC2626] hover:bg-[#B91C1C] text-white font-mono text-xs uppercase font-bold tracking-wider rounded cursor-pointer transition-colors disabled:opacity-50 mt-2"
              >
                {registering ? "Provisioning..." : "Create User"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
