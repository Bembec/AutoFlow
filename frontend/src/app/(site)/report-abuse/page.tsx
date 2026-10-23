import type { Metadata } from "next";
import { S } from "@/lib/site-i18n";
import { Suspense } from "react";

import { AbuseForm } from "@/components/site/AbuseForm";
import { SiteHero } from "@/components/site/SiteChrome";

export const instant = true;

export const metadata: Metadata = { title: "Report abuse" };

export default function ReportAbusePage() {
  return (
    <>
      <SiteHero eyebrow="Trust and safety" title="Report spam or phishing">
        <p>
          <S t={"Got an email sent through our platform that looks like spam or phishing? Tell us. Every report is reviewed, and a workspace that breaks the rules can be stopped from sending."} />
        </p>
      </SiteHero>
      <div className="mx-auto max-w-2xl px-4 pb-20 sm:px-6">
        <Suspense fallback={<div className="h-96 rounded-2xl border border-slate-200" />}>
          <AbuseForm />
        </Suspense>
      </div>
    </>
  );
}
