import { useEffect, useRef, useState } from "react"
import axios from "axios"
import "./App.css"

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000").replace(/\/+$/, "")

const TOPICS = [
  {
    name: "Periods",
    sub: "Cycles, flow, cramps, delayed periods, irregular timing",
    glow: "rgba(223, 96, 140, 0.18)",
    line: "rgba(180, 39, 94, 0.2)",
    glowX: "86%",
    glowY: "14%",
    glowSize: "11.5rem",
    questions: [
      "Why is my period late?",
      "Are blood clots during my period normal?",
      "What causes severe period cramps?",
      "Why did my period come early this month?",
      "What can make periods suddenly irregular?",
      "How much bleeding is considered heavy?",
      "Is spotting between periods normal?",
      "Can stress delay my period?",
      "Why is my period lasting longer than usual?",
      "When should I worry about missed periods?",
    ],
  },
  {
    name: "PCOS and Endometriosis",
    sub: "Symptoms, warning signs, patterns, and what to look for",
    glow: "rgba(199, 116, 76, 0.18)",
    line: "rgba(163, 81, 44, 0.2)",
    glowX: "14%",
    glowY: "18%",
    glowSize: "12rem",
    questions: [
      "What are common signs of PCOS?",
      "What are common signs of endometriosis?",
      "How are PCOS and endometriosis different?",
      "Can PCOS cause missed or irregular periods?",
      "Can endometriosis cause pain outside my period?",
      "What symptoms make doctors suspect PCOS?",
      "What symptoms make doctors suspect endometriosis?",
      "Can you have both PCOS and endometriosis?",
      "When should I get checked for PCOS?",
      "When should I get checked for endometriosis?",
    ],
  },
  {
    name: "PMS and PMDD",
    sub: "Mood, fatigue, emotional shifts, and period-linked symptoms",
    glow: "rgba(155, 106, 189, 0.16)",
    line: "rgba(121, 72, 158, 0.18)",
    glowX: "82%",
    glowY: "78%",
    glowSize: "11rem",
    questions: [
      "What is the difference between PMS and PMDD?",
      "How do I know if my symptoms are more than normal PMS?",
      "Can PMDD cause anxiety or depression before my period?",
      "When do PMS symptoms usually start and end?",
      "What are the most common PMDD symptoms?",
      "Why do I feel exhausted before my period?",
      "Can hormones make mood swings worse before a period?",
      "What helps with PMS bloating and fatigue?",
      "When should I talk to a doctor about PMS or PMDD?",
      "Can PMDD get worse over time?",
    ],
  },
  {
    name: "Birth Control",
    sub: "Pills, IUDs, side effects, missed doses, and expectations",
    glow: "rgba(74, 146, 146, 0.16)",
    line: "rgba(42, 114, 114, 0.18)",
    glowX: "18%",
    glowY: "78%",
    glowSize: "11.5rem",
    questions: [
      "What are common birth control side effects?",
      "Is spotting normal after starting birth control?",
      "What should I do if I miss a birth control pill?",
      "How long does it take for pill side effects to settle?",
      "Can birth control make my period lighter or disappear?",
      "Can an IUD cause cramping or irregular bleeding?",
      "When should I worry about birth control side effects?",
      "Can birth control affect mood?",
      "What bleeding changes are normal with an implant?",
      "How do I know if my birth control is not suiting me?",
    ],
  },
  {
    name: "Ovulation and Tracking",
    sub: "Fertility signs, ovulation timing, and cycle tracking basics",
    glow: "rgba(217, 150, 64, 0.18)",
    line: "rgba(177, 112, 29, 0.2)",
    glowX: "74%",
    glowY: "24%",
    glowSize: "11rem",
    questions: [
      "How can I track ovulation and fertility signs?",
      "What are common signs that I am ovulating?",
      "When in my cycle am I most fertile?",
      "How reliable is cervical mucus for tracking ovulation?",
      "Can irregular periods make ovulation harder to predict?",
      "Do ovulation tests always work accurately?",
      "What does basal body temperature actually tell me?",
      "Can I ovulate without obvious symptoms?",
      "How many days before ovulation can I get pregnant?",
      "When should I seek help for fertility concerns?",
    ],
  },
  {
    name: "Common Myths",
    sub: "Debunking misinformation with grounded medical context",
    glow: "rgba(208, 89, 125, 0.18)",
    line: "rgba(169, 45, 93, 0.2)",
    glowX: "16%",
    glowY: "84%",
    glowSize: "12rem",
    questions: [
      "Can you get pregnant during your period?",
      "Does stress really affect periods?",
      "Can birth control cause permanent infertility?",
      "Do blood clots always mean something is wrong?",
      "Is severe period pain just something to put up with?",
      "Can PCOS happen even if I am not overweight?",
      "Does a regular period always mean I am ovulating?",
      "Can you still get pregnant if your periods are irregular?",
      "Is vaginal discharge always a sign of infection?",
      "What are some common myths about periods and reproductive health?",
    ],
  },
]

const EXAMPLES = [
  "Why is my period late?",
  "What are signs of PCOS?",
  "Are clots normal?",
  "What is PMDD?",
]

const LANDING_SECTIONS = [
  {
    title: "What is Her Circle?",
    paragraphs: [
      "Her Circle is a reproductive health companion for the questions that usually begin with uncertainty. Is this normal? Should I worry? Why is my cycle different this month? It gives people one calm place to ask about periods, hormones, fertility, contraception, pelvic pain, discharge, cycle changes, and common myths without having to open ten tabs and piece together an answer alone.",
      "The idea behind it is simple. Health information should not feel cold, punishing, or hard to understand when you are already feeling vulnerable. It should meet you gently, explain things clearly, and help you feel a little more steady by the time you finish reading.",
    ],
  },
  {
    title: "Why is Her Circle different?",
    paragraphs: [
      "A lot of health tools either sound too robotic or too vague. Her Circle tries to sit somewhere more human. It is built to feel calmer than a general chatbot and more approachable than a wall of medical text, while still staying grounded in trusted guidance.",
      "The answer is meant to tell you the important part first, explain it in language that feels readable, and keep the sources visible so the response feels transparent instead of mysterious. When it helps, Her Circle can also bring in grounded lived-experience context, not to replace medical information, but to make the answer feel less abstract and more connected to what real people often notice or ask.",
    ],
  },
  {
    title: "How Her Circle works?",
    paragraphs: [
      "You ask in plain language, the same way you would type into notes or text a friend. Her Circle then works through the question by identifying the topic, checking for relevant medical guidance, and shaping the response around the clearest next thing you likely need to understand.",
      "If there is useful supporting context, it can bring that in too, but the answer stays focused on being readable and grounded. What comes back is meant to feel direct, supportive, and transparent, with visible sources so you can understand not just the answer itself, but why that answer is being given.",
      "The whole experience is designed to make reproductive health information feel less intimidating to approach and easier to return to when you need it again.",
    ],
  },
]

const UI_LABELS = {
  default: {
    seekCare: "When To Seek Care",
    relatedDiscussions: "Related Discussions",
    sources: "Sources",
    discussionSuffix: "discussion",
    loadingTitle: "Searching trusted guidance",
    loadingSequence: "Checking medical sources -> Looking for grounded experiences -> Building a clear answer",
    disclaimer:
      "Her Circle is for informational support only and does not replace professional medical advice, diagnosis, or treatment.",
  },
  ar: {
    seekCare: "متى يجب طلب الرعاية الطبية",
    relatedDiscussions: "نقاشات ذات صلة",
    sources: "المصادر",
    discussionSuffix: "نقاش",
    loadingTitle: "جارٍ البحث عن إرشادات موثوقة",
    loadingSequence: "جارٍ التحقق من المصادر الطبية -> جارٍ البحث عن تجارب واقعية -> جارٍ إعداد إجابة واضحة",
    disclaimer:
      "هير سيركل مخصص للدعم المعلوماتي فقط ولا يُغني عن المشورة الطبية المهنية أو التشخيص أو العلاج.",
  },
  he: {
    seekCare: "מתי לפנות לטיפול רפואי",
    relatedDiscussions: "דיונים קשורים",
    sources: "מקורות",
    discussionSuffix: "דיון",
    loadingTitle: "מחפש מידע מהימן",
    loadingSequence: "בודק מקורות רפואיים -> מחפש חוויות אמיתיות -> בונה תשובה ברורה",
    disclaimer:
      "Her Circle נועד לתמיכה מידעית בלבד ואינו מחליף ייעוץ רפואי מקצועי, אבחון או טיפול.",
  },
  bn: {
    seekCare: "কখন চিকিৎসকের পরামর্শ নেবেন",
    relatedDiscussions: "সম্পর্কিত আলোচনা",
    sources: "সূত্র",
    discussionSuffix: "আলোচনা",
    loadingTitle: "বিশ্বস্ত তথ্য খোঁজা হচ্ছে",
    loadingSequence: "চিকিৎসা-সংক্রান্ত উৎস দেখা হচ্ছে -> বাস্তব অভিজ্ঞতা খোঁজা হচ্ছে -> পরিষ্কার উত্তর তৈরি করা হচ্ছে",
    disclaimer:
      "Her Circle শুধুমাত্র তথ্যভিত্তিক সহায়তার জন্য এবং এটি পেশাদার চিকিৎসা পরামর্শ, রোগনির্ণয় বা চিকিৎসার বিকল্প নয়।",
  },
  hi: {
    seekCare: "कब डॉक्टर से मिलें",
    relatedDiscussions: "संबंधित चर्चाएँ",
    sources: "स्रोत",
    discussionSuffix: "चर्चा",
    loadingTitle: "विश्वसनीय मार्गदर्शन खोजा जा रहा है",
    loadingSequence: "चिकित्सीय स्रोत देखे जा रहे हैं -> वास्तविक अनुभव खोजे जा रहे हैं -> स्पष्ट उत्तर तैयार किया जा रहा है",
    disclaimer:
      "Her Circle केवल जानकारी के लिए है और यह पेशेवर चिकित्सीय सलाह, निदान या उपचार का विकल्प नहीं है।",
  },
  ta: {
    seekCare: "எப்போது மருத்துவரை அணுக வேண்டும்",
    relatedDiscussions: "தொடர்புடைய விவாதங்கள்",
    sources: "ஆதாரங்கள்",
    discussionSuffix: "விவாதம்",
    loadingTitle: "நம்பகமான வழிகாட்டுதலை தேடுகிறது",
    loadingSequence: "மருத்துவ ஆதாரங்கள் சரிபார்க்கப்படுகின்றன -> உண்மை அனுபவங்கள் தேடப்படுகின்றன -> தெளிவான பதில் உருவாக்கப்படுகிறது",
    disclaimer:
      "Her Circle தகவல் ஆதரவுக்காக மட்டுமே; இது தொழில்முறை மருத்துவ ஆலோசனை, கண்டறிதல் அல்லது சிகிச்சைக்கு மாற்றாகாது.",
  },
  es: {
    seekCare: "Cuándo buscar atención médica",
    relatedDiscussions: "Conversaciones relacionadas",
    sources: "Fuentes",
    discussionSuffix: "discusión",
    loadingTitle: "Buscando orientación confiable",
    loadingSequence: "Revisando fuentes médicas -> Buscando experiencias reales -> Redactando una respuesta clara",
    disclaimer:
      "Her Circle es solo para apoyo informativo y no sustituye el consejo médico profesional, el diagnóstico ni el tratamiento.",
  },
}

function makeId(prefix) {
  return globalThis.crypto?.randomUUID?.() ?? `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function sanitizeInlineCitations(text, sourceLookup = []) {
  if (!text) return text

  const sourceCount = sourceLookup.length
  const sanitized = text.replace(/\[(\d+)\]/g, (_, rawNumber) => {
    const citationNumber = Number(rawNumber)
    return sourceCount > 0 && citationNumber <= sourceCount ? `[${citationNumber}]` : ""
  })

  return sanitized
    .replace(/(?:\[\d+\]){2,}/g, (match) => [...new Set(match.match(/\[\d+\]/g) || [])].join(""))
    .replace(/[^\S\r\n]{2,}/g, " ")
    .replace(/\s+([,.;:!?])/g, "$1")
    .replace(/\(\s+\)/g, "")
    .trim()
}

function renderCitationTokens(text, keyPrefix, sourceLookup, messageId) {
  const parts = text.split(/(\[\d+\])/g).filter(Boolean)

  return parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (!match) {
      return <span key={`${keyPrefix}-plain-${index}`}>{part}</span>
    }

    const citationNumber = Number(match[1])
    const source = sourceLookup[citationNumber - 1]
    if (!source || !messageId) {
      return <sup key={`${keyPrefix}-missing-${index}`} className="inline-citation inline-citation-missing">{part}</sup>
    }

    return (
      <a
        key={`${keyPrefix}-citation-${index}`}
        href={`#source-${messageId}-${citationNumber}`}
        className="inline-citation"
        title={source.name}
        aria-label={`Jump to source ${citationNumber}: ${source.name}`}
      >
        {part}
      </a>
    )
  })
}

function renderInlineMarkdown(text, keyPrefix, sourceLookup = [], messageId = "") {
  const tokens = text.split(/(\*\*.*?\*\*|\*.*?\*)/g).filter(Boolean)

  return tokens.map((token, index) => {
    if (token.startsWith("**") && token.endsWith("**") && token.length > 4) {
      return (
        <strong key={`${keyPrefix}-strong-${index}`}>
          {renderCitationTokens(token.slice(2, -2), `${keyPrefix}-strong-${index}`, sourceLookup, messageId)}
        </strong>
      )
    }

    if (token.startsWith("*") && token.endsWith("*") && token.length > 2) {
      return (
        <em key={`${keyPrefix}-em-${index}`}>
          {renderCitationTokens(token.slice(1, -1), `${keyPrefix}-em-${index}`, sourceLookup, messageId)}
        </em>
      )
    }

    return (
      <span key={`${keyPrefix}-text-${index}`}>
        {renderCitationTokens(token, `${keyPrefix}-text-${index}`, sourceLookup, messageId)}
      </span>
    )
  })
}

function normalizeMarkdownText(text) {
  return text
    .replace(/:\s*\*\s+/g, ":\n\n- ")
    .replace(/\s+\*\s+(?=[A-Z0-9])/g, "\n- ")
}

function renderMarkdownBlocks(text, sourceLookup = [], messageId = "") {
  if (!text) return null

  return normalizeMarkdownText(text)
    .trim()
    .split(/\n\s*\n/)
    .map((block, blockIndex) => {
      const lines = block.split("\n").map((line) => line.trim()).filter(Boolean)
      const unordered = lines.every((line) => /^[-*]\s+/.test(line))
      const ordered = lines.every((line) => /^\d+\.\s+/.test(line))

      if (unordered) {
        return (
          <ul key={`ul-${blockIndex}`} className="answer-list">
            {lines.map((line, lineIndex) => (
              <li key={`ul-item-${blockIndex}-${lineIndex}`}>
                {renderInlineMarkdown(line.replace(/^[-*]\s+/, ""), `ul-${blockIndex}-${lineIndex}`, sourceLookup, messageId)}
              </li>
            ))}
          </ul>
        )
      }

      if (ordered) {
        return (
          <ol key={`ol-${blockIndex}`} className="answer-list answer-list-ordered">
            {lines.map((line, lineIndex) => (
              <li key={`ol-item-${blockIndex}-${lineIndex}`}>
                {renderInlineMarkdown(line.replace(/^\d+\.\s+/, ""), `ol-${blockIndex}-${lineIndex}`, sourceLookup, messageId)}
              </li>
            ))}
          </ol>
        )
      }

      return (
        <p key={`p-${blockIndex}`} className="answer-paragraph">
          {renderInlineMarkdown(block, `p-${blockIndex}`, sourceLookup, messageId)}
        </p>
      )
    })
}

function AnswerMarkdown({ text, onSelection, sources, messageId }) {
  const normalizedText = sanitizeInlineCitations(text, sources)

  return (
    <div className="answer-text" onMouseUp={onSelection} onKeyUp={onSelection}>
      {renderMarkdownBlocks(normalizedText, sources, messageId)}
    </div>
  )
}

function buildHistory(messages) {
  return messages
    .filter((message) => (message.role === "user" && message.content) || (message.role === "assistant" && message.status === "done"))
    .map((message) => {
      if (message.role === "user") {
        return { role: "user", content: message.content }
      }

      const assistantParts = [message.answer, message.myth, message.see_doctor_if].filter(Boolean)
      return { role: "assistant", content: assistantParts.join("\n\n") }
    })
}

function detectScriptLanguage(text) {
  if (!text) return "default"
  if (/[\u0600-\u06FF]/.test(text)) return "ar"
  if (/[\u0590-\u05FF]/.test(text)) return "he"
  if (/[\u0980-\u09FF]/.test(text)) return "bn"
  if (/[\u0900-\u097F]/.test(text)) return "hi"
  if (/[\u0B80-\u0BFF]/.test(text)) return "ta"

  const lowered = text.toLowerCase()
  const spanishMarkers = [" qué ", " por qué ", " menstruación ", " embarazo ", " dolor ", " período ", " periodo "]
  if (spanishMarkers.some((marker) => lowered.includes(marker.trim()) || lowered.includes(marker))) {
    return "es"
  }

  return "default"
}

function getUiLabels(languageKey) {
  const resolvedKey = languageKey || "default"
  return UI_LABELS[resolvedKey] || UI_LABELS.default
}

function detectMessageLanguage(text) {
  const languageKey = detectScriptLanguage(text)
  return languageKey || "default"
}

function getDiscussionLabel(url, index, labels) {
  try {
    const { pathname } = new URL(url)
    const parts = pathname.split("/").filter(Boolean)
    const subredditIndex = parts.findIndex((part) => part === "r")
    if (subredditIndex >= 0 && parts[subredditIndex + 1]) {
      return `r/${parts[subredditIndex + 1]} ${labels.discussionSuffix}`
    }
  } catch {
    return `${labels.relatedDiscussions} ${index + 1}`
  }

  return `${labels.relatedDiscussions} ${index + 1}`
}

function buildCopyPayload(message, labels) {
  const sections = [message.answer?.trim()].filter(Boolean)

  if (message.myth) {
    sections.push(`Myth Check\n${message.myth.trim()}`)
  }

  if (message.see_doctor_if) {
    sections.push(`${labels.seekCare}\n${message.see_doctor_if.trim()}`)
  }

  if (message.sources?.length) {
    const sourceLines = message.sources.map((source, index) => `${index + 1}. ${source.name} — ${source.url}`)
    sections.push(`${labels.sources}\n${sourceLines.join("\n")}`)
  }

  return sections.join("\n\n")
}

function buildConversationShareText(messages) {
  const parts = ["Her Circle conversation"]

  messages.forEach((message) => {
    if (message.role === "user" && message.content) {
      parts.push(`You: ${message.content.trim()}`)
      return
    }

    if (message.role !== "assistant" || message.status !== "done") {
      return
    }

    const labels = getUiLabels(message.languageKey)
    const assistantSections = [message.answer?.trim()].filter(Boolean)

    if (message.myth) {
      assistantSections.push(`Myth Check\n${message.myth.trim()}`)
    }

    if (message.see_doctor_if) {
      assistantSections.push(`${labels.seekCare}\n${message.see_doctor_if.trim()}`)
    }

    if (message.sources?.length) {
      const sourceLines = message.sources.map((source, index) => `${index + 1}. ${source.name} — ${source.url}`)
      assistantSections.push(`${labels.sources}\n${sourceLines.join("\n")}`)
    }

    parts.push(`Her Circle: ${assistantSections.join("\n\n")}`)
  })

  return parts.join("\n\n")
}

function buildConversationShareToken(messages) {
  const payload = messages
    .filter((message) => {
      if (message.role === "user") {
        return Boolean(message.content)
      }
      return message.role === "assistant" && message.status === "done" && Boolean(message.answer)
    })
    .map((message) => {
      if (message.role === "user") {
        return {
          role: "user",
          content: message.content,
          languageKey: message.languageKey || "default",
        }
      }

      return {
        role: "assistant",
        status: "done",
        languageKey: message.languageKey || "default",
        answer: message.answer || "",
        sources: message.sources || [],
        reddit_experiences: message.reddit_experiences || [],
        myth: message.myth || null,
        see_doctor_if: message.see_doctor_if || null,
      }
    })

  const bytes = new TextEncoder().encode(JSON.stringify(payload))
  let binary = ""
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "")
}

function buildConversationShareLink(messages) {
  const token = buildConversationShareToken(messages)
  if (!token) return ""

  const url = new URL(window.location.href)
  url.searchParams.set("chat", token)
  url.hash = ""
  return url.toString()
}

function parseSharedConversation(token) {
  try {
    const normalized = token.replace(/-/g, "+").replace(/_/g, "/")
    const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4))
    const binary = atob(`${normalized}${padding}`)
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
    const decoded = new TextDecoder().decode(bytes)
    const parsed = JSON.parse(decoded)
    if (!Array.isArray(parsed)) return []

    return parsed
      .filter((message) => message && (message.role === "user" || message.role === "assistant"))
      .map((message, index) => ({
        id: makeId(`${message.role}-${index}`),
        role: message.role,
        status: message.role === "assistant" ? "done" : undefined,
        content: message.role === "user" ? message.content || "" : undefined,
        languageKey: message.languageKey || "default",
        answer: message.role === "assistant" ? message.answer || "" : undefined,
        sources: message.role === "assistant" ? message.sources || [] : undefined,
        reddit_experiences: message.role === "assistant" ? message.reddit_experiences || [] : undefined,
        myth: message.role === "assistant" ? message.myth || null : undefined,
        see_doctor_if: message.role === "assistant" ? message.see_doctor_if || null : undefined,
      }))
  } catch {
    return []
  }
}

function clearBrowserSelection() {
  const selection = window.getSelection()
  selection?.removeAllRanges()
}

export default function App() {
  const [question, setQuestion] = useState("")
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState("landing")
  const [activeTopic, setActiveTopic] = useState(null)
  const [selectedExcerpt, setSelectedExcerpt] = useState("")
  const [copiedMessageId, setCopiedMessageId] = useState(null)
  const [shareStatus, setShareStatus] = useState("")
  const composerRef = useRef(null)

  const resizeComposer = (value) => {
    const textarea = composerRef.current
    if (!textarea) return
    textarea.style.height = "0px"
    const nextHeight = Math.min(textarea.scrollHeight, 220)
    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY = textarea.scrollHeight > 220 ? "auto" : "hidden"
    if (!value) {
      textarea.scrollTop = 0
    }
  }

  useEffect(() => {
    resizeComposer(question)
  }, [question])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const sharedChat = params.get("chat")
    if (!sharedChat) return

    const parsedMessages = parseSharedConversation(sharedChat)
    if (!parsedMessages.length) return

    setMessages(parsedMessages)
    setView("chat")
  }, [])

  useEffect(() => {
    if (view !== "chat") return
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" })
  }, [messages, loading, view])

  useEffect(() => {
    if (!activeTopic) return undefined

    const previousOverflow = document.body.style.overflow
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setActiveTopic(null)
      }
    }

    document.body.style.overflow = "hidden"
    window.addEventListener("keydown", handleEscape)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener("keydown", handleEscape)
    }
  }, [activeTopic])

  const openLanding = () => {
    setActiveTopic(null)
    setView("landing")
    setLoading(false)
  }

  const openChat = (prefill = "") => {
    setActiveTopic(null)
    setView("chat")
    if (prefill) {
      setQuestion(prefill)
    }
  }

  const openTopics = () => {
    setActiveTopic(null)
    setView("topics")
    setLoading(false)
  }

  const startNewChat = () => {
    setActiveTopic(null)
    setMessages([])
    setQuestion("")
    setSelectedExcerpt("")
    setCopiedMessageId(null)
    setShareStatus("")
    setLoading(false)
    clearBrowserSelection()
    resizeComposer("")
    const url = new URL(window.location.href)
    url.searchParams.delete("chat")
    window.history.replaceState({}, "", url.toString())
    setView("chat")
    setTimeout(() => composerRef.current?.focus(), 0)
  }

  const ask = async (q) => {
    const query = (q || question).trim()
    if (!query || loading) return
    const languageKey = detectMessageLanguage(query)

    const userMessage = {
      id: makeId("user"),
      role: "user",
      content: query,
      languageKey,
    }

    const assistantMessage = {
      id: makeId("assistant"),
      role: "assistant",
      status: "loading",
      languageKey,
    }

    const history = buildHistory(messages)

    setView("chat")
    setSelectedExcerpt("")
    setQuestion("")
    resizeComposer("")
    setLoading(true)
    setMessages((current) => [...current, userMessage, assistantMessage])

    try {
      const res = await axios.post(`${API_BASE_URL}/ask`, {
        question: query,
        history,
      })

      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessage.id
            ? {
                ...message,
                status: "done",
                answer: sanitizeInlineCitations(res.data.answer, res.data.sources || []),
                sources: res.data.sources || [],
                reddit_experiences: res.data.reddit_experiences || [],
                myth: res.data.myth,
                see_doctor_if: res.data.see_doctor_if,
              }
            : message,
        ),
      )
    } catch (requestError) {
      const backendMessage = requestError?.response?.data?.error || "Something went wrong. Please try again."
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessage.id
            ? {
                ...message,
                status: "error",
                error: backendMessage,
              }
            : message,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  const startTopic = (prompt) => {
    setView("chat")
    ask(prompt)
  }

  const openTopicQuestions = (topic) => {
    setActiveTopic(topic)
  }

  const closeTopicQuestions = () => {
    setActiveTopic(null)
  }

  const chooseTopicQuestion = (prompt) => {
    setActiveTopic(null)
    setView("chat")
    ask(prompt)
  }

  const handleAnswerSelection = (event) => {
    const selection = window.getSelection()
    const selectedText = selection?.toString().trim() || ""

    if (!selectedText) {
      setSelectedExcerpt("")
      return
    }

    const anchorNode = selection?.anchorNode
    if (!anchorNode || !event.currentTarget.contains(anchorNode)) {
      setSelectedExcerpt("")
      return
    }

    setSelectedExcerpt(selectedText.slice(0, 280))
  }

  const useSelectedExcerpt = () => {
    if (!selectedExcerpt) return
    setQuestion(`Can you explain this part more clearly: ${selectedExcerpt}`)
    setView("chat")
    setTimeout(() => composerRef.current?.focus(), 0)
  }

  const cancelSelection = () => {
    setSelectedExcerpt("")
    clearBrowserSelection()
  }

  const copyAnswer = async (message) => {
    const labels = getUiLabels(message.languageKey)
    const payload = buildCopyPayload(message, labels)
    if (!payload) return

    try {
      await navigator.clipboard.writeText(payload)
      setCopiedMessageId(message.id)
      window.setTimeout(() => {
        setCopiedMessageId((current) => (current === message.id ? null : current))
      }, 1800)
    } catch {
      setCopiedMessageId(null)
    }
  }

  const shareConversation = async () => {
    if (!messages.length) return
    const shareLink = buildConversationShareLink(messages)
    if (!shareLink) return

    try {
      await navigator.clipboard.writeText(shareLink)
      setShareStatus("Copied")
    } catch {
      const fallbackText = buildConversationShareText(messages)
      if (!fallbackText.trim()) {
        setShareStatus("")
        return
      }
      try {
        await navigator.clipboard.writeText(fallbackText)
        setShareStatus("Copied")
      } catch {
        setShareStatus("")
        return
      }
    }

    window.setTimeout(() => {
      setShareStatus("")
    }, 1800)
  }

  return (
    <div className="app-shell">
      <div className="page-glow page-glow-left" />
      <div className="page-glow page-glow-right" />

      <header className="header">
        <div className="header-inner">
          <button type="button" className="brand-button" onClick={openLanding}>
            Her Circle
          </button>

          <nav className="nav-links">
            {view === "chat" && (
              <>
                {messages.length > 0 && (
                  <button
                    type="button"
                    className="nav-link nav-link-icon"
                    onClick={shareConversation}
                    aria-label={shareStatus === "Copied" ? "Link copied" : "Copy conversation link"}
                    title={shareStatus === "Copied" ? "Link copied" : "Copy conversation link"}
                  >
                    <span className="nav-link-share-icon" aria-hidden="true" />
                  </button>
                )}
                <button
                  type="button"
                  className="nav-link nav-link-icon"
                  onClick={startNewChat}
                  aria-label="Start new chat"
                  title="Start new chat"
                >
                  <span className="nav-link-plus-icon" aria-hidden="true">+</span>
                </button>
              </>
            )}
            <button
              type="button"
              className={`nav-link ${view === "chat" ? "active" : ""}`}
              onClick={() => openChat()}
            >
              Chat
            </button>
            <button
              type="button"
              className={`nav-link ${view === "topics" ? "active" : ""}`}
              onClick={openTopics}
            >
              Topics
            </button>
          </nav>
        </div>
      </header>

      <main className={`container container-${view}`}>
        {view === "landing" && (
          <section className="landing-layout">
            <section className="landing-hero">
              <h1>One place to understand what your body may be trying to tell you.</h1>
              <p className="landing-copy">
                Ask about periods, hormones, fertility, contraception, pelvic pain, and common myths
                in a space that feels calmer, clearer, and more grounded than a general web search.
              </p>
            </section>

            <section className="landing-sections">
              {LANDING_SECTIONS.map((item) => (
                <section key={item.title} className="landing-section">
                  <h2>{item.title}</h2>
                  <div className="landing-section-body">
                    {item.paragraphs.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </div>
                </section>
              ))}
            </section>
          </section>
        )}

        {view === "topics" && (
          <section className="topics-page">
            <div className="page-intro">
              <h2>Browse the questions people most often start with.</h2>
              <p>
                Choose a topic to open a set of common starter questions, then pick the one you want
                to ask in chat.
              </p>
            </div>

            <div className="topic-grid">
              {TOPICS.map((topic) => (
                <button
                  key={topic.name}
                  type="button"
                  className="topic-card"
                  style={{
                    "--topic-glow": topic.glow,
                    "--topic-line": topic.line,
                    "--topic-glow-x": topic.glowX,
                    "--topic-glow-y": topic.glowY,
                    "--topic-glow-size": topic.glowSize,
                  }}
                  onClick={() => openTopicQuestions(topic)}
                >
                  <div className="topic-card-copy">
                    <div className="topic-name">{topic.name}</div>
                    <div className="topic-sub">{topic.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {view === "chat" && (
          <section className="chat-layout">
            <div className="chat-thread">
              {!messages.length && !loading && (
                <div className="chat-empty">
                  <div className="chat-empty-title">What would you like to understand today?</div>
                  <div className="chat-empty-sub">
                    Ask in simple language. Her Circle will answer with cited medical sources and
                    grounded context when available.
                  </div>
                  <div className="example-prompt-row">
                    {EXAMPLES.map((example) => (
                      <button key={example} type="button" className="example-btn" onClick={() => startTopic(example)}>
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message) => {
                if (message.role === "user") {
                  return (
                    <div key={message.id} className="message-row message-row-user">
                      <div className="message-bubble message-bubble-user">{message.content}</div>
                    </div>
                  )
                }

                if (message.status === "loading") {
                  const labels = getUiLabels(message.languageKey)
                  return (
                    <div key={message.id} className="message-row">
                      <div className="message-panel">
                        <div className="loading-title">
                          {labels.loadingTitle}
                          <span className="loading-dots">
                            <span />
                            <span />
                            <span />
                          </span>
                        </div>
                        <div className="loading-sequence">{labels.loadingSequence}</div>
                      </div>
                    </div>
                  )
                }

                if (message.status === "error") {
                  return (
                    <div key={message.id} className="message-row">
                      <div className="message-panel error-panel">{message.error}</div>
                    </div>
                  )
                }

                return (
                  <div key={message.id} className="message-row">
                    <div className="message-panel assistant-panel">
                      {(() => {
                        const labels = getUiLabels(message.languageKey)
                        return (
                          <>
                      <AnswerMarkdown
                        text={message.answer}
                        onSelection={handleAnswerSelection}
                        sources={message.sources || []}
                        messageId={message.id}
                      />

                      {message.myth && (
                        <div className="myth-box">
                          <div className="myth-label">Myth Check</div>
                          <div className="myth-text">{message.myth}</div>
                        </div>
                      )}

                      {message.see_doctor_if && (
                        <div className="doctor-box">
                          <div className="doctor-label">{labels.seekCare}</div>
                          <div className="doctor-text">{message.see_doctor_if}</div>
                        </div>
                      )}

                      {message.reddit_experiences?.length > 0 && (
                        <div className="result-section">
                          <div className="section-label">{labels.relatedDiscussions}</div>
                          <div className="reddit-compact-list">
                            {message.reddit_experiences.map((experience, index) => (
                              <div key={`${experience.url}-${index}`} className="reddit-compact-item">
                                <div className="reddit-link-label">{getDiscussionLabel(experience.url, index, labels)}</div>
                                <a href={experience.url} target="_blank" rel="noreferrer" className="inline-arrow-link" aria-label="Open Reddit discussion">
                                  <span className="inline-arrow-link-icon" />
                                </a>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.sources?.length > 0 && (
                        <div className="result-section result-section-sources">
                          <div className="section-label">{labels.sources}</div>
                          <div className="source-compact-list">
                            {message.sources.map((source, index) => (
                              <a
                                key={`${source.url}-${index}`}
                                id={`source-${message.id}-${index + 1}`}
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                                className="source-compact-item"
                              >
                                <span className="source-compact-index">{index + 1}.</span>
                                <span className="source-compact-name">{source.name}</span>
                                <span className="inline-arrow-link inline-arrow-link-static" aria-hidden="true">
                                  <span className="inline-arrow-link-icon" />
                                </span>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="assistant-footer">
                        <div className="assistant-disclaimer">
                          {labels.disclaimer}
                        </div>
                        <button
                          type="button"
                          className="assistant-copy-btn"
                          onClick={() => copyAnswer(message)}
                          aria-label={copiedMessageId === message.id ? "Copied" : "Copy answer"}
                          title={copiedMessageId === message.id ? "Copied" : "Copy answer"}
                        >
                          <span className="assistant-copy-icon" aria-hidden="true" />
                        </button>
                      </div>
                          </>
                        )
                      })()}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="chat-composer-wrap">
              {selectedExcerpt && (
                <div className="selection-followup-bar">
                  <div className="selection-followup-copy">
                    Ask a follow-up about: <span>{selectedExcerpt}</span>
                  </div>
                  <div className="selection-followup-actions">
                    <button type="button" className="selection-followup-btn" onClick={useSelectedExcerpt}>
                      Ask
                    </button>
                    <button
                      type="button"
                      className="selection-dismiss-btn"
                      onClick={cancelSelection}
                      aria-label="Clear selected text"
                    >
                      ×
                    </button>
                  </div>
                </div>
              )}

              <div className="chat-composer">
                <textarea
                  ref={composerRef}
                  className="composer-input"
                  value={question}
                  onChange={(e) => {
                    setQuestion(e.target.value)
                    resizeComposer(e.target.value)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      ask()
                    }
                  }}
                  onFocus={() => resizeComposer(question)}
                  placeholder="Message Her Circle..."
                  disabled={loading}
                  rows={1}
                />

                <div className="composer-footer">
                  <div className="composer-footer-right">
                    <button type="button" className="mic-btn" aria-label="Voice input coming soon" disabled>
                      <span className="mic-icon" />
                    </button>
                    <button
                      type="button"
                      className="send-btn"
                      onClick={() => ask()}
                      disabled={loading}
                      aria-label={loading ? "Thinking" : "Send message"}
                    >
                      <span className="send-arrow" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>

      {activeTopic && (
        <div className="topic-modal-backdrop" onClick={closeTopicQuestions}>
          <div
            className="topic-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="topic-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="topic-modal-header">
              <div>
                <h3 id="topic-modal-title">{activeTopic.name}</h3>
                <p>{activeTopic.sub}</p>
              </div>
              <button
                type="button"
                className="topic-modal-close"
                onClick={closeTopicQuestions}
                aria-label="Close topic questions"
              >
                ×
              </button>
            </div>

            <div className="topic-modal-body">
              <div className="topic-question-list">
                {activeTopic.questions.map((questionText) => (
                  <button
                    key={questionText}
                    type="button"
                    className="topic-question-btn"
                    onClick={() => chooseTopicQuestion(questionText)}
                  >
                    {questionText}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
