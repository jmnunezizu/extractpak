import { StrictMode, useEffect, useState } from "react";
import type { ComponentType, CSSProperties } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  AudioWaveform,
  CheckCircle2,
  Code2,
  Download,
  FileArchive,
  Github,
  GitPullRequest,
  Hammer,
  HeartHandshake,
  History,
  Info,
  Layers3,
  PackageCheck,
  ShieldCheck,
  Terminal,
  Wrench,
} from "lucide-react";
import { installGoogleAnalytics } from "./analytics";
import type { ThemeId } from "./siteConfig";
import { siteConfig } from "./siteConfig";
import "./styles.css";

const installCommand =
  "curl -fsSL https://github.com/jmnunezizu/scummkit/releases/latest/download/install.sh | sh";

type Feature = {
  icon: ComponentType<{ size?: number; strokeWidth?: number }>;
  title: string;
  body: string;
};

const baseUrl = import.meta.env.BASE_URL;
const logoUrl = `${baseUrl}scummkit-logo-web.png`;
const heroStyle = {
  "--hero-image": `url("${baseUrl}hero-pixel-coastal-archive.png")`,
} as CSSProperties;

const themes = [
  { id: "harbor", label: "Harbor" },
  { id: "harbor-deep", label: "Deep" },
  { id: "harbor-moon", label: "Moonlit" },
  { id: "harbor-chart", label: "Chartroom" },
] satisfies Array<{ id: ThemeId; label: string }>;

const capabilities: Feature[] = [
  {
    icon: FileArchive,
    title: "Extracts classic resources",
    body: "Reads the Special Edition PAK layouts and pulls out the classic SCUMM data used by ScummVM.",
  },
  {
    icon: AudioWaveform,
    title: "Processes speech and music",
    body: "Decodes XACT wave banks, prepares speech samples, and builds ScummVM speech archives.",
  },
  {
    icon: Hammer,
    title: "Applies talkie patches",
    body: "Uses bundled Ultimate Talkie patch and table data with permission, without shipping game assets.",
  },
  {
    icon: PackageCheck,
    title: "Writes playable folders",
    body: "Creates local output directories containing patched resources, speech archives, and music files.",
  },
];

const pipeline = [
  { label: "Local game files", detail: "PAK + audio banks", icon: Archive },
  { label: "SCUMMKit build", detail: "extract, patch, encode", icon: Wrench },
  { label: "Ultimate Talkie folder", detail: "classic graphics + speech archive", icon: PackageCheck },
];

const timeline = [
  ["extractpak", "A focused C helper for exploring Monkey Island Special Edition PAK archives."],
  ["native builders", "Python orchestration replaced shell-script-heavy workflows with checked, testable steps."],
  [
    "Ultimate Talkie output",
    "The Secret of Monkey Island and Monkey Island 2 builds now produce ScummVM-compatible local folders.",
  ],
  ["builder independence", "Analysis commands continue to map patch data, scripts, speech tables, and resource changes."],
];

const technicalNotes: Feature[] = [
  {
    icon: Layers3,
    title: "XWB parsing",
    body: "SCUMMKit inspects and extracts XACT wave banks used for speech, ambience, music, and sound effects.",
  },
  {
    icon: Terminal,
    title: "MONSTER archives",
    body: "The packer creates deterministic ScummVM compressed speech archives from processed samples and monster.tbl.",
  },
  {
    icon: Code2,
    title: "Sound-effect injection",
    body: "Native resource injection adds high-quality sound effects for The Secret of Monkey Island while preserving SCUMM resource structure.",
  },
  {
    icon: GitPullRequest,
    title: "Research tooling",
    body: "Inspection commands help compare patches, rooms, scripts, speech manifests, and audio references.",
  },
];

function App() {
  const [theme, setTheme] = useState<ThemeId>(siteConfig.defaultTheme);

  useEffect(() => {
    installGoogleAnalytics(siteConfig.googleAnalyticsMeasurementId);
  }, []);

  return (
    <div className="siteShell" data-theme={theme}>
      {siteConfig.showThemeSelector && (
        <aside className="themeLab" aria-label="Theme selector">
          <span>Theme</span>
          <div>
            {themes.map((item) => (
              <button
                className={theme === item.id ? "active" : ""}
                key={item.id}
                type="button"
                onClick={() => setTheme(item.id)}
                aria-pressed={theme === item.id}
              >
                {item.label}
              </button>
            ))}
          </div>
        </aside>
      )}

      <header className="hero">
        <div className="heroBackdrop" style={heroStyle} aria-hidden="true" />
        <nav className="nav" aria-label="Primary navigation">
          <a className="brand" href="#top" aria-label="SCUMMKit home">
            <img src={logoUrl} alt="" />
          </a>
          <div className="navLinks">
            <a href="#how">How it works</a>
            <a href="#technical">Technical notes</a>
            <a href="#install">Install</a>
            <a className="iconLink" href="https://github.com/jmnunezizu/scummkit" aria-label="GitHub repository">
              <Github size={18} />
            </a>
          </div>
        </nav>

        <section className="heroContent" id="top">
          <p className="eyebrow">Native tools for ScummVM-compatible Ultimate Talkie builds</p>
          <h1>SCUMMKit</h1>
          <p className="heroText">
            Build local Monkey Island Ultimate Talkie Edition folders from your own Special Edition files, with
            extraction, patching, audio conversion, and archive packing handled by one cross-platform toolkit.
          </p>
          <div className="heroActions">
            <a className="button primary" href="#install">
              <Download size={18} />
              Install
            </a>
            <a className="button secondary" href="https://github.com/jmnunezizu/scummkit">
              <Github size={18} />
              GitHub
            </a>
          </div>
        </section>
      </header>

      <main>
        <section className="summaryBand" aria-label="Current support">
          <div>
            <span className="metric">Monkey Island</span>
            <span>The Secret of Monkey Island, with Ogg speech, root music, and SBL sound effects</span>
          </div>
          <div>
            <span className="metric">Monkey Island 2</span>
            <span>LeChuck's Revenge, Ogg primary with FLAC/MP3 speech archive paths</span>
          </div>
        </section>

        <section className="section intro">
          <div className="sectionText">
            <p className="eyebrow">Why it exists</p>
            <h2>A modern build path for a very specific preservation job.</h2>
          </div>
          <div className="copyGrid">
            <p>
              SCUMMKit started as practical tooling around the Special Edition PAK files and grew into a native build
              pipeline for Ultimate Talkie-style ScummVM outputs. It is designed for people who own the games and want
              a repeatable local build without redistributing copyrighted data.
            </p>
            <p>
              The project keeps the boring parts explicit: required tools are checked before use, unsupported formats
              fail with clear diagnostics, and generated output stays on the user's machine.
            </p>
          </div>
        </section>

        <section className="section capabilities" id="how">
          <div className="sectionText">
            <p className="eyebrow">What it does</p>
            <h2>The build steps, without the old ceremony.</h2>
          </div>
          <div className="featureGrid">
            {capabilities.map((item) => (
              <article className="featureCard" key={item.title}>
                <item.icon size={24} />
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="pipelineSection" aria-labelledby="pipeline-title">
          <div className="sectionText">
            <p className="eyebrow">Build pipeline</p>
            <h2 id="pipeline-title">A small chain of explicit transformations.</h2>
          </div>
          <div className="pipeline">
            {pipeline.map((item, index) => (
              <div className="pipelineStep" key={item.label}>
                <div className="pipelineIcon">
                  <item.icon size={24} />
                </div>
                <div>
                  <h3>{item.label}</h3>
                  <p>{item.detail}</p>
                </div>
                {index < pipeline.length - 1 && <span className="connector" aria-hidden="true" />}
              </div>
            ))}
          </div>
        </section>

        <section className="section support">
          <div className="sectionText">
            <p className="eyebrow">Support matrix</p>
            <h2>Two games, separate build paths.</h2>
          </div>
          <div className="supportTable" role="table" aria-label="Supported games">
            <div className="tableRow header" role="row">
              <span role="columnheader">Game</span>
              <span role="columnheader">Outputs</span>
              <span role="columnheader">Notes</span>
            </div>
            <div className="tableRow" role="row">
              <span role="cell">The Secret of Monkey Island</span>
              <span role="cell">Ogg speech, root music, SBL sound effects</span>
              <span role="cell">FLAC/MP3/raw are intentionally not advertised until validated end to end.</span>
            </div>
            <div className="tableRow" role="row">
              <span role="cell">Monkey Island 2: LeChuck's Revenge</span>
              <span role="cell">Ogg, FLAC, and MP3 compressed speech archives</span>
              <span role="cell">Ogg is the primary validated target. Raw monster.sou is not implemented.</span>
            </div>
          </div>
        </section>

        <section className="technicalBand" id="technical">
          <div className="sectionText">
            <p className="eyebrow">Technical notes</p>
            <h2>Reverse-engineering work kept close to the build.</h2>
          </div>
          <div className="technicalGrid">
            {technicalNotes.map((item) => (
              <article className="technicalItem" key={item.title}>
                <item.icon size={22} />
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section historySection">
          <div className="sectionText">
            <p className="eyebrow">Project history</p>
            <h2>From extractor to native build pipeline.</h2>
          </div>
          <ol className="timeline">
            {timeline.map(([title, body]) => (
              <li key={title}>
                <History size={18} />
                <div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="legalBand" aria-labelledby="legal-title">
          <ShieldCheck size={28} />
          <div>
            <h2 id="legal-title">Local inputs only.</h2>
            <p>
              SCUMMKit does not include commercial game assets or generated game output. It expects legally owned local
              Special Edition files and writes build products to a folder you control.
            </p>
          </div>
        </section>

        <section className="installSection" id="install">
          <div className="sectionText">
            <p className="eyebrow">Install</p>
            <h2>Install the latest release locally.</h2>
            <p>
              The installer is user-local by default. It installs SCUMMKit under your home directory, compiles the PAK
              extractor, and points the command at an isolated Python environment.
            </p>
          </div>
          <div className="terminalPanel" aria-label="Install command">
            <div className="terminalTop">
              <Terminal size={18} />
              <span>shell</span>
            </div>
            <code>{installCommand}</code>
          </div>
          <div className="installLinks">
            <a className="button primary" href="https://github.com/jmnunezizu/scummkit/releases/latest">
              <CheckCircle2 size={18} />
              Latest release
            </a>
            <a className="button secondary" href="https://github.com/jmnunezizu/scummkit#quick-start">
              <Info size={18} />
              Quick start
            </a>
          </div>
        </section>
      </main>

      <footer>
        <div>
          <img src={logoUrl} alt="SCUMMKit" />
          <p>Open-source tooling for local, legally owned game preservation workflows.</p>
          <p className="trademarkNote">
            Monkey Island is a trademark of Lucasfilm Ltd. ScummVM is a trademark of the ScummVM project.
            SCUMMKit is independent and is not affiliated with or endorsed by Lucasfilm, Disney, or ScummVM.
          </p>
        </div>
        <a href="https://github.com/jmnunezizu/scummkit">
          <HeartHandshake size={18} />
          Contribute on GitHub
        </a>
      </footer>
    </div>
  );
}

export default App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
