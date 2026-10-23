import type { Metadata } from "next";

import { S } from "@/lib/site-i18n";
import { SiteCta, SiteHero } from "@/components/site/SiteChrome";
import { TemplateGallery } from "@/components/site/SiteLists";

export const instant = true;

export const metadata: Metadata = { title: "Templates" };

export default function TemplatesPage() {
  return (
    <>
      <SiteHero eyebrow="Templates" title="Ready-made automations">
        <p><S t={"Install one in a click, test it with an example, then switch it on. Every template can be edited afterwards."} /></p>
      </SiteHero>
      <div className="mx-auto max-w-6xl px-4 pb-8 sm:px-6">
        <TemplateGallery />
      </div>
      <SiteCta title="Don't see yours? Describe it in a sentence." />
    </>
  );
}
