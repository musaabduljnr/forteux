"use client";

import { useState } from "react";
import { Icon } from "./icons";

interface FAQItem {
  id: string;
  question: string;
  answer: string;
}

const faqs: FAQItem[] = [
  {
    id: "faq-1",
    question: "What is Forteux?",
    answer:
      "Forteux is an AI-powered UI/UX design auditing and design intelligence platform. It analyzes uploaded interface screenshots, detects usability and visual hierarchy problems, visualizes findings with normalized bounding boxes, evaluates multi-screen flow consistency, extracts design system tokens, and synthesizes structured redesign prompts for Google Stitch.",
  },
  {
    id: "faq-2",
    question: "Who is Forteux designed for?",
    answer:
      "Forteux is built for product designers, UX researchers, front-end engineers, and product teams who want an objective, evidence-based second pair of eyes on their digital interfaces before shipping to users.",
  },
  {
    id: "faq-3",
    question: "How does AI interface auditing work?",
    answer:
      "You upload one or more interface screenshots (PNG, JPEG, WebP). Forteux's AI vision engine inspects layout hierarchy, typography contrast, interactive touch clearance, and safe-area constraints. It identifies potential design problems and returns structured findings with severity classifications, observable evidence, and bounding-box coordinates overlaid on your screen.",
  },
  {
    id: "faq-4",
    question: "Can Forteux analyse multiple screens?",
    answer:
      "Yes. Forteux's multi-screen journey engine analyzes sequential workflows (such as onboarding, checkout, or settings flows). It detects cross-screen discrepancies like button placement drift, typography shifts, and broken interaction continuity across consecutive steps.",
  },
  {
    id: "faq-5",
    question: "Can Forteux generate redesign prompts?",
    answer:
      "Yes. You can select specific findings from an audit and generate a comprehensive redesign prompt optimized for Google Stitch. The prompt includes layout directives, design tokens, and accessibility constraints to guide rapid UI prototyping.",
  },
  {
    id: "faq-6",
    question: "Does Forteux replace Figma or Google Stitch?",
    answer:
      "No. Forteux is a design intelligence and auditing layer that complements your creative tools. It identifies where your interfaces fall short and provides structured prompt specifications that you can take into Google Stitch or Figma to design your next iteration.",
  },
  {
    id: "faq-7",
    question: "Can I use my own UX documentation?",
    answer:
      "Yes. Forteux includes a Knowledge Library where you can upload design systems, company brand guidelines, and accessibility standards (PDF, DOCX, TXT, Markdown). The RAG (Retrieval-Augmented Generation) pipeline grounds AI audit findings in your team's specific guidelines with source citations.",
  },
  {
    id: "faq-8",
    question: "How are uploaded screenshots protected?",
    answer:
      "Screenshots and audit artifacts are stored in private Supabase Storage buckets accessible exclusively through short-lived presigned URLs (300-second TTL). Multi-tenant isolation is enforced at both the application API layer and PostgreSQL Row Level Security (RLS) policies. Your design data is isolated to your organization.",
  },
];

export function LandingFAQ() {
  const [openId, setOpenId] = useState<string | null>("faq-1");

  const toggleFAQ = (id: string) => {
    setOpenId(openId === id ? null : id);
  };

  return (
    <section className="landing-section section-alternate" id="faq">
      <div className="landing-section-header">
        <span className="section-eyebrow">COMMON QUESTIONS</span>
        <h2 className="landing-section-heading">Frequently Asked Questions</h2>
        <p className="landing-section-subhead">
          Everything you need to know about the Forteux AI design intelligence platform.
        </p>
      </div>

      <div className="faq-container">
        {faqs.map((faq) => {
          const isOpen = openId === faq.id;
          return (
            <div key={faq.id} className={`faq-item ${isOpen ? "faq-open" : ""}`}>
              <button
                type="button"
                className="faq-question-btn"
                onClick={() => toggleFAQ(faq.id)}
                aria-expanded={isOpen}
                aria-controls={`faq-answer-${faq.id}`}
              >
                <span className="faq-question-text">{faq.question}</span>
                <span className="faq-chevron-icon">
                  <Icon name={isOpen ? "close" : "down"} size={16} />
                </span>
              </button>
              {isOpen && (
                <div id={`faq-answer-${faq.id}`} className="faq-answer-pane" role="region">
                  <p>{faq.answer}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
