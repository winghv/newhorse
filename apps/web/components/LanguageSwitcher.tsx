"use client";

import { useLocale } from "next-intl";
import { useRouter, usePathname } from "@/i18n/routing";
import { Globe } from "lucide-react";

const localeLabels: Record<string, string> = {
  en: "EN",
  zh: "中文",
};

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const nextLocale = locale === "en" ? "zh" : "en";

  const handleSwitch = () => {
    router.replace(pathname, { locale: nextLocale });
  };

  return (
    <button
      onClick={handleSwitch}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
      title={nextLocale === "zh" ? "切换到中文" : "Switch to English"}
    >
      <Globe className="w-3.5 h-3.5" />
      <span>{localeLabels[locale]}</span>
    </button>
  );
}

export default LanguageSwitcher;
