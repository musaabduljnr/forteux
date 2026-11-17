"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Audit, KnowledgeDocument, Project, UploadedScreen, User } from "@/lib/types";
import { demoAudits, demoKnowledge, demoProjects, demoUser } from "@/lib/demo-data";

interface ToastMessage {
  id: string;
  message: string;
  tone: "success" | "info" | "error";
}

interface NewAuditInput {
  id?: string;
  projectId: string;
  name: string;
  mode: Audit["mode"];
  screens: UploadedScreen[];
  context?: Audit["context"];
  analysisFocus?: Audit["analysisFocus"];
  isDemo?: boolean;
}

interface AppStateValue {
  projects: Project[];
  audits: Audit[];
  documents: KnowledgeDocument[];
  selectedProjectId: string;
  user: User;
  toasts: ToastMessage[];
  setSelectedProjectId: (id: string) => void;
  updateUser: (update: Partial<Pick<User, "displayName" | "email">>) => void;
  createProject: (name: string, description: string) => string;
  updateProject: (id: string, update: Partial<Pick<Project, "name" | "description" | "status">>) => void;
  deleteProject: (id: string) => void;
  createAudit: (input: NewAuditInput) => string;
  updateAudit: (id: string, update: Partial<Audit>) => void;
  reorderAuditScreens: (auditId: string, from: number, to: number) => void;
  addDocument: (document: KnowledgeDocument) => void;
  removeDocument: (id: string) => void;
  notify: (message: string, tone?: ToastMessage["tone"]) => void;
  dismissToast: (id: string) => void;
}

interface PersistedState {
  projects: Project[];
  audits: Audit[];
  documents: KnowledgeDocument[];
  selectedProjectId: string;
  user: User;
}

const STORAGE_KEY = "forteux-frontend-demo-v1";

const AppStateContext = createContext<AppStateValue | null>(null);

function makeId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>(demoProjects);
  const [audits, setAudits] = useState<Audit[]>(demoAudits);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>(demoKnowledge);
  const [selectedProjectId, setSelectedProjectId] = useState(demoProjects[0].id);
  const [user, setUser] = useState<User>(demoUser);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as Partial<PersistedState>;
        if (Array.isArray(parsed.projects)) setProjects(parsed.projects);
        if (Array.isArray(parsed.audits)) {
          setAudits(parsed.audits.map((audit) => ({
            ...audit,
            screens: audit.screens.map((screen) => ({
              ...screen,
              previewUrl: screen.previewUrl?.startsWith("/") ? screen.previewUrl : undefined,
            })),
          })));
        }
        if (Array.isArray(parsed.documents)) setDocuments(parsed.documents);
        if (typeof parsed.selectedProjectId === "string") setSelectedProjectId(parsed.selectedProjectId);
        if (parsed.user && typeof parsed.user.displayName === "string" && typeof parsed.user.email === "string") setUser(parsed.user);
      }
    } catch {
      setToasts([{ id: makeId("toast"), message: "Saved demo data could not be loaded. The session will use sample data.", tone: "error" }]);
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const safeAudits = audits.map((audit) => ({
      ...audit,
      screens: audit.screens.map((screen) => ({
        ...screen,
        previewUrl: screen.previewUrl?.startsWith("/") ? screen.previewUrl : undefined,
      })),
    }));
    const state: PersistedState = { projects, audits: safeAudits, documents, selectedProjectId, user };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      setToasts((current) => [
        ...current.slice(-2),
        { id: makeId("toast"), message: "Browser storage is full; some demo changes may not persist.", tone: "error" },
      ]);
    }
  }, [audits, documents, hydrated, projects, selectedProjectId, user]);

  const notify = useCallback((message: string, tone: ToastMessage["tone"] = "info") => {
    const id = makeId("toast");
    setToasts((current) => [...current.slice(-2), { id, message, tone }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4200);
  }, []);

  const createProject = useCallback((name: string, description: string) => {
    const id = makeId("project");
    const project: Project = { id, name, description, updatedAt: new Date().toISOString(), status: "Active" };
    setProjects((current) => [project, ...current]);
    setSelectedProjectId(id);
    return id;
  }, []);

  const updateUser = useCallback((update: Partial<Pick<User, "displayName" | "email">>) => {
    setUser((current) => {
      const displayName = update.displayName ?? current.displayName;
      const initials = displayName.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("");
      return { ...current, ...update, avatarInitials: initials || current.avatarInitials };
    });
  }, []);

  const updateProject = useCallback((id: string, update: Partial<Pick<Project, "name" | "description" | "status">>) => {
    setProjects((current) => current.map((project) =>
      project.id === id ? { ...project, ...update, updatedAt: new Date().toISOString() } : project,
    ));
  }, []);

  const deleteProject = useCallback((id: string) => {
    const remaining = projects.filter((project) => project.id !== id);
    setProjects(remaining);
    setSelectedProjectId((selected) => selected === id ? remaining[0]?.id ?? "" : selected);
    setAudits((current) => current.filter((audit) => audit.projectId !== id));
    setDocuments((current) => current.filter((document) => document.projectId !== id));
  }, [projects]);

  const createAudit = useCallback((input: NewAuditInput) => {
    const id = input.id || makeId("audit");
    const audit: Audit = {
      id,
      projectId: input.projectId,
      name: input.name,
      mode: input.mode,
      status: input.isDemo === false ? "ready" : "demo",
      createdAt: new Date().toISOString(),
      screens: input.screens,
      issues: [],
      context: input.context,
      analysisFocus: input.analysisFocus,
      isDemo: input.isDemo ?? true,
    };
    setAudits((current) => [audit, ...current]);
    return id;
  }, []);

  const updateAudit = useCallback((id: string, update: Partial<Audit>) => {
    setAudits((current) => current.map((audit) => audit.id === id ? { ...audit, ...update } : audit));
  }, []);

  const reorderAuditScreens = useCallback((auditId: string, from: number, to: number) => {
    setAudits((current) => current.map((audit) => {
      if (audit.id !== auditId || from < 0 || from >= audit.screens.length || to < 0 || to >= audit.screens.length) return audit;
      const screens = [...audit.screens];
      const [moved] = screens.splice(from, 1);
      screens.splice(to, 0, moved);
      return { ...audit, screens };
    }));
  }, []);

  const addDocument = useCallback((document: KnowledgeDocument) => {
    setDocuments((current) => [document, ...current]);
  }, []);

  const removeDocument = useCallback((id: string) => {
    setDocuments((current) => current.filter((document) => document.id !== id));
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo<AppStateValue>(() => ({
    projects,
    audits,
    documents,
    selectedProjectId,
    user,
    toasts,
    setSelectedProjectId,
    updateUser,
    createProject,
    updateProject,
    deleteProject,
    createAudit,
    updateAudit,
    reorderAuditScreens,
    addDocument,
    removeDocument,
    notify,
    dismissToast,
  }), [
    projects, audits, documents, selectedProjectId, user, toasts, createProject, updateProject, updateUser,
    deleteProject, createAudit, updateAudit, reorderAuditScreens, addDocument, removeDocument,
    notify, dismissToast,
  ]);

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateValue {
  const context = useContext(AppStateContext);
  if (!context) throw new Error("useAppState must be used within AppStateProvider");
  return context;
}
