import React, { useState, useMemo, useEffect } from 'react';
import { 
  Search, 
  Printer, 
  Bookmark, 
  ExternalLink, 
  ShieldCheck, 
  AlertCircle, 
  PhoneCall, 
  Layers, 
  CheckCircle2, 
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { 
  guidanceSections, 
  disclaimer, 
  quickExitNotice, 
  QUICK_EXIT_URL 
} from '../content/guidance.js';
import { Button } from '../components/common/Button';

export const Guide: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isMobileTocOpen, setIsMobileTocOpen] = useState<boolean>(false);

  // Handle hash scrolling on initial load or change
  useEffect(() => {
    if (window.location.hash) {
      const id = window.location.hash.replace('#', '');
      const el = document.getElementById(id);
      if (el) {
        setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    }
  }, []);

  const handlePrint = () => {
    window.print();
  };

  // Client-side search filtering
  const filteredSections = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return guidanceSections;

    return guidanceSections
      .map((section) => {
        const titleMatch = section.title.toLowerCase().includes(q);
        const introMatch = (section.shortIntro || section.intro || section.details || '').toLowerCase().includes(q);

        // Filter habits if present
        const matchingHabits = section.habits?.filter(
          (h) => h.title.toLowerCase().includes(q) || h.body.toLowerCase().includes(q)
        );

        // Filter categories if present
        const matchingCategories = section.categories?.filter(
          (c) =>
            c.title.toLowerCase().includes(q) ||
            c.guidelines.some((g) => g.toLowerCase().includes(q))
        );

        // Filter mistakes if present
        const matchingMistakes = section.mistakes?.filter((m) =>
          m.toLowerCase().includes(q)
        );

        // Filter resources if present
        const matchingResources = section.resources?.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            r.number.toLowerCase().includes(q) ||
            r.description.toLowerCase().includes(q)
        );

        const hasSubMatches =
          (matchingHabits && matchingHabits.length > 0) ||
          (matchingCategories && matchingCategories.length > 0) ||
          (matchingMistakes && matchingMistakes.length > 0) ||
          (matchingResources && matchingResources.length > 0);

        if (titleMatch || introMatch || hasSubMatches) {
          return {
            ...section,
            habits: titleMatch || introMatch ? section.habits : matchingHabits,
            categories: titleMatch || introMatch ? section.categories : matchingCategories,
            mistakes: titleMatch || introMatch ? section.mistakes : matchingMistakes,
            resources: titleMatch || introMatch ? section.resources : matchingResources,
          };
        }
        return null;
      })
      .filter(Boolean) as typeof guidanceSections;
  }, [searchQuery]);

  return (
    <div className="space-y-6 max-w-4xl pb-16">
      {/* Page Header */}
      <div className="pb-4 border-b border-[#E6E4DF] flex flex-col sm:flex-row sm:items-center justify-between gap-4 print:border-b-2 print:border-black">
        <div>
          <h1 className="text-xl font-semibold text-[#1C1917] tracking-tight">
            Evidence Guide & Awareness
          </h1>
          <p className="text-xs text-[#6B6862] mt-1 print:text-black">
            Practical, trauma-informed guidance on safely gathering, preserving, and organizing digital records.
          </p>
        </div>

        <div className="flex items-center gap-2 print:hidden">
          <Button variant="secondary" size="sm" onClick={handlePrint}>
            <Printer className="w-3.5 h-3.5" />
            <span>Print or save PDF</span>
          </Button>
        </div>
      </div>

      {/* Search Bar - Client Side Only */}
      <div className="print:hidden">
        <div className="relative">
          <Search className="w-4 h-4 text-[#9C9890] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search guide by keyword (e.g. whatsapp, screenshot, audio, deleted, report)..."
            className="w-full bg-white border border-[#E6E4DF] rounded-md pl-9 pr-4 py-2 text-xs text-[#1C1917] placeholder-[#9C9890] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] transition-all"
            aria-label="Search guide content"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-[#6B6862] hover:text-[#1C1917]"
            >
              Clear
            </button>
          )}
        </div>
        {searchQuery && (
          <p className="text-[11px] text-[#6B6862] mt-1.5">
            Showing results matching &ldquo;{searchQuery}&rdquo; ({filteredSections.length} section{filteredSections.length === 1 ? '' : 's'})
          </p>
        )}
      </div>

      {/* Main Layout: Sticky Table of Contents on Desktop + Main Content */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
        {/* Table of Contents - Desktop Sticky / Mobile Collapsible */}
        <aside className="md:col-span-1 md:sticky md:top-20 space-y-3 print:hidden">
          {/* Mobile toggle */}
          <div className="md:hidden">
            <button
              type="button"
              onClick={() => setIsMobileTocOpen(!isMobileTocOpen)}
              className="w-full flex items-center justify-between p-2.5 bg-white border border-[#E6E4DF] rounded text-xs font-medium text-[#1C1917]"
            >
              <span className="flex items-center gap-1.5">
                <Bookmark className="w-3.5 h-3.5 text-[#0F766E]" />
                <span>On this page</span>
              </span>
              {isMobileTocOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          <div
            className={`bg-white border border-[#E6E4DF] rounded-md p-3.5 space-y-2 md:block ${
              isMobileTocOpen ? 'block' : 'hidden md:block'
            }`}
          >
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-[#6B6862] flex items-center gap-1.5 pb-1 border-b border-[#F0EFEB]">
              <Bookmark className="w-3.5 h-3.5 text-[#0F766E]" />
              <span>Contents</span>
            </h2>
            <nav className="space-y-1 text-xs">
              {guidanceSections.map((sec) => (
                <a
                  key={sec.id}
                  href={`#${sec.id}`}
                  onClick={() => setIsMobileTocOpen(false)}
                  className="block px-2 py-1.5 rounded text-[#57534E] hover:text-[#0F766E] hover:bg-[#F8F8F6] transition-colors truncate"
                >
                  {sec.title}
                </a>
              ))}
              <a
                href="#browsing-safety"
                onClick={() => setIsMobileTocOpen(false)}
                className="block px-2 py-1.5 rounded text-[#57534E] hover:text-[#0F766E] hover:bg-[#F8F8F6] transition-colors truncate"
              >
                Privacy & Quick exit
              </a>
            </nav>
          </div>
        </aside>

        {/* Content Body */}
        <div className="md:col-span-3 space-y-8">
          {filteredSections.length === 0 ? (
            <div className="bg-white border border-[#E6E4DF] rounded-md p-6 text-center space-y-2">
              <p className="text-sm font-medium text-[#1C1917]">No guidance topics matched your search.</p>
              <p className="text-xs text-[#6B6862]">Try a different keyword or reset the search to view all sections.</p>
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="text-xs text-[#0F766E] underline hover:text-[#0D655E] pt-2 inline-block"
              >
                View all sections
              </button>
            </div>
          ) : (
            filteredSections.map((section) => (
              <section
                key={section.id}
                id={section.id}
                className="bg-white border border-[#E6E4DF] rounded-md p-5 sm:p-6 space-y-4 scroll-mt-20 print:border-none print:p-0 print:space-y-3"
              >
                <div className="border-b border-[#F0EFEB] pb-3">
                  <h2 className="text-base font-semibold text-[#1C1917]">
                    {section.title}
                  </h2>
                  {(section.shortIntro || section.intro) && (
                    <p className="text-xs text-[#6B6862] mt-1 leading-relaxed">
                      {section.shortIntro || section.intro}
                    </p>
                  )}
                </div>

                {section.details && (
                  <p className="text-xs text-[#44403C] leading-relaxed">
                    {section.details}
                  </p>
                )}

                {/* Section 2: Five habits */}
                {section.habits && (
                  <div className="space-y-3">
                    {section.habits.map((h) => (
                      <div
                        key={h.num}
                        className="p-3.5 bg-[#FAF9F5] border border-[#EAE8E1] rounded text-xs space-y-1"
                      >
                        <div className="font-medium text-[#1C1917] flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-[#E6F4F1] text-[#0F766E] font-semibold flex items-center justify-center text-[11px] shrink-0">
                            {h.num}
                          </span>
                          <span>{h.title}</span>
                        </div>
                        <p className="text-[#57534E] pl-7 leading-relaxed">
                          {h.body}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Section 3: What to save by type */}
                {section.categories && (
                  <div className="space-y-4">
                    {section.categories.map((cat) => (
                      <div
                        key={cat.id}
                        className="border border-[#EAE8E1] rounded p-4 space-y-2 bg-[#FDFDFC]"
                      >
                        <h3 className="text-xs font-semibold text-[#1C1917] flex items-center gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#0F766E] shrink-0" />
                          <span>{cat.title}</span>
                        </h3>
                        <ul className="space-y-1.5 pl-5 list-disc text-xs text-[#57534E] leading-relaxed">
                          {cat.guidelines.map((tip, idx) => (
                            <li key={idx}>{tip}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {/* Section 4: Common mistakes */}
                {section.mistakes && (
                  <div className="space-y-2">
                    <ul className="space-y-2 text-xs text-[#57534E]">
                      {section.mistakes.map((mistake, idx) => (
                        <li
                          key={idx}
                          className="flex items-start gap-2.5 p-2.5 bg-[#FBFBF9] border border-[#EAE8E1] rounded"
                        >
                          <AlertCircle className="w-4 h-4 text-[#B45309] shrink-0 mt-0.5" />
                          <span className="leading-relaxed">{mistake}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Section 5: Emergency help & resources */}
                {section.resources && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                    {section.resources.map((res, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 bg-[#F6FAF9] border border-[#D5EAE6] rounded text-xs space-y-1.5"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold text-[#1C1917]">{res.name}</span>
                          <span className="font-mono text-[11px] font-bold text-[#0F766E] bg-white border border-[#D5EAE6] px-1.5 py-0.5 rounded shrink-0">
                            {res.number}
                          </span>
                        </div>
                        <p className="text-[#57534E] text-[11px] leading-relaxed">
                          {res.description}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            ))
          )}

          {/* Privacy and Quick exit explanation */}
          <section
            id="browsing-safety"
            className="bg-white border border-[#E6E4DF] rounded-md p-5 sm:p-6 space-y-3 scroll-mt-20 print:border-none print:p-0"
          >
            <div className="border-b border-[#F0EFEB] pb-2">
              <h2 className="text-base font-semibold text-[#1C1917]">
                {quickExitNotice.title}
              </h2>
              <p className="text-xs text-[#6B6862] mt-1 leading-relaxed">
                {quickExitNotice.summary}
              </p>
            </div>

            <div className="p-3 bg-[#FFFDF5] border border-[#F3E7C4] rounded text-xs text-[#785412] leading-relaxed">
              <span className="font-semibold">{quickExitNotice.warning}</span>
            </div>

            <div className="space-y-1.5 pt-1">
              <h3 className="text-xs font-semibold text-[#1C1917]">How to protect your privacy:</h3>
              <ul className="list-disc pl-5 space-y-1.5 text-xs text-[#57534E] leading-relaxed">
                {quickExitNotice.privacyTips.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
            </div>
          </section>

          {/* Quiet Footer Legal Disclaimer */}
          <footer className="pt-4 border-t border-[#E6E4DF] text-xs text-[#6B6862] leading-relaxed space-y-2 print:border-t-2 print:border-black">
            <div className="flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-[#9C9890] shrink-0 mt-0.5" />
              <p>{disclaimer.text}</p>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
};
