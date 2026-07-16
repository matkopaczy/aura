"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, TeamMember, addReception, getTeam, removeTeamMember } from "@/lib/api";

export default function TeamSection() {
  const t = useTranslations("team");
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    getTeam()
      .then(setMembers)
      .catch(() => setError("error"));
  }, []);

  useEffect(reload, [reload]);

  async function add(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await addReception(email, password);
      setEmail("");
      setPassword("");
      reload();
    } catch (e) {
      setError(e instanceof ApiError && e.status === 409 ? "emailTaken" : "error");
    }
  }

  async function remove(id: string) {
    try {
      await removeTeamMember(id);
      reload();
    } catch {
      setError("error");
    }
  }

  const roleLabel = (role: TeamMember["role"]) =>
    role === "owner" ? t("roleOwner") : t("roleReception");

  return (
    <section style={{ marginTop: "3rem", borderTop: "1px solid #e0e0e0", paddingTop: "1.5rem" }}>
      <h2>{t("title")}</h2>
      <p>{t("hint")}</p>
      <table>
        <tbody>
          {members.map((m) => (
            <tr key={m.id}>
              <td>{m.email}</td>
              <td>{roleLabel(m.role)}</td>
              <td>
                {m.role === "reception" && (
                  <button type="button" onClick={() => remove(m.id)}>
                    {t("remove")}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>{t("addTitle")}</h3>
      {error !== null && <p className="error">{t(error)}</p>}
      <form onSubmit={add}>
        <label htmlFor="team-email">{t("email")}</label>
        <input
          id="team-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="team-password">{t("password")}</label>
        <input
          id="team-password"
          type="password"
          minLength={10}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">{t("add")}</button>
      </form>
    </section>
  );
}
