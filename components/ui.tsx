"use client";

import { useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";
import { Icon, type IconName } from "./icons";
import type { Severity } from "@/lib/types";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {action && <div className="page-heading-actions">{action}</div>}
    </div>
  );
}

export function Button({
  children,
  variant = "primary",
  icon,
  href,
  onClick,
  type = "button",
  form,
  disabled,
  className = "",
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  icon?: IconName;
  href?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  form?: string;
  disabled?: boolean;
  className?: string;
}) {
  const classNames = `button button-${variant} ${className}`.trim();
  const content = <>{icon && <Icon name={icon} size={17} />}{children}</>;
  if (href) return <Link href={href} className={classNames}>{content}</Link>;
  return <button type={type} form={form} className={classNames} onClick={onClick} disabled={disabled}>{content}</button>;
}

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "blue" | "demo";
  className?: string;
}) {
  return <span className={`badge badge-${tone} ${className}`.trim()}>{children}</span>;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge tone={severity === "critical" || severity === "high" ? "danger" : severity === "medium" ? "warning" : "neutral"}>{severity}</Badge>;
}

export function MetricCard({
  label,
  value,
  detail,
  icon,
  tint = "blue",
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: IconName;
  tint?: "blue" | "green" | "amber" | "violet";
}) {
  return (
    <article className="metric-card">
      <div className={`metric-icon metric-icon-${tint}`}><Icon name={icon} size={19} /></div>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

export function EmptyState({
  icon = "file",
  title,
  description,
  action,
}: {
  icon?: IconName;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><Icon name={icon} size={22} /></div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function SectionTitle({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-title">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Modal({
  title,
  description,
  children,
  onClose,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
}) {
  const dialogRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    const initialFocus = dialog?.querySelector<HTMLElement>("input, select, textarea, button:not(.icon-button)")
      ?? dialog?.querySelector<HTMLElement>("button");
    initialFocus?.focus();
    return () => previousFocus?.focus();
  }, []);

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="dialog" ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabIndex={-1} onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
        if (event.key === "Tab") {
          const focusable = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("input, select, textarea, button")).filter((element) => !element.hasAttribute("disabled"));
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }
      }}>
        <div className="dialog-heading">
          <div><h2 id="modal-title">{title}</h2>{description && <p>{description}</p>}</div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog"><Icon name="close" /></button>
        </div>
        <div className="dialog-content">{children}</div>
        {footer && <div className="dialog-footer">{footer}</div>}
      </section>
    </div>
  );
}
