import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

function LandingPage({ user, t, onLoginClick, onRegisterClick }) {
  const navigate = useNavigate();
  const mountedRef = useRef(true);

  /* Kinetic typography */
  useEffect(() => {
    const letters = document.querySelectorAll(".hero-letter");
    letters.forEach((el, i) => {
      el.style.animationDelay = `${i * 0.07 + 0.3}s`;
    });
  }, []);

  /* Intersection observer */
  useEffect(() => {
    const sections = document.querySelectorAll(".landing-section");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("visible");
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -50px 0px" },
    );
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  /* Hero parallax */
  useEffect(() => {
    const handleScroll = () => {
      const y = window.scrollY;
      const hero = document.querySelector(".landing-hero");
      if (!hero) return;
      const h = hero.offsetHeight;
      if (y < h) {
        const inner = hero.querySelector(".hero-inner");
        if (inner) {
          inner.style.transform = `translateY(${y * 0.25}px)`;
          inner.style.opacity = 1 - y / h;
        }
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  /* Risograph dot trail */
  useEffect(() => {
    let last = 0;
    const onMove = (e) => {
      if (!mountedRef.current) return;
      const now = Date.now();
      if (now - last < 55) return;
      last = now;
      const dot = document.createElement("div");
      dot.className = "riso-dot";
      dot.style.left = `${e.clientX}px`;
      dot.style.top = `${e.clientY}px`;
      document.body.appendChild(dot);
      setTimeout(() => {
        if (dot.parentNode) dot.remove();
      }, 900);
    };
    window.addEventListener("mousemove", onMove);
    return () => {
      mountedRef.current = false;
      window.removeEventListener("mousemove", onMove);
    };
  }, []);

  const features = [
    [t("landing.f1l"), t("landing.f1d")],
    [t("landing.f2l"), t("landing.f2d")],
    [t("landing.f3l"), t("landing.f3d")],
    [t("landing.f4l"), t("landing.f4d")],
    [t("landing.f5l"), t("landing.f5d")],
    [t("landing.f6l"), t("landing.f6d")],
  ];

  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="hero-inner">
          <div className="hero-tag">{t("landing.heroTag")}</div>
          <div className="hero-kinetic">
            <div className="hero-line">
              {"GROWTH".split("").map((ch, i) => (
                <span key={i} className="hero-letter">
                  {ch}
                </span>
              ))}
            </div>
            <div className="hero-line hero-line-indent">
              {"QUEST".split("").map((ch, i) => (
                <span
                  key={i + 6}
                  className={`hero-letter${i === 0 ? " hero-letter-accent" : ""}`}
                >
                  {ch}
                </span>
              ))}
            </div>
          </div>
          <p className="hero-subtitle">{t("landing.heroSub")}</p>
        </div>
        <div className="hero-scroll">
          <span>{t("landing.scroll")}</span>
          <div className="hero-scroll-line" />
        </div>
      </section>

      <section className="landing-section" id="manifesto">
        <div className="section-inner">
          <div className="section-kick">{t("landing.k1")}</div>
          <div className="manifesto-layout">
            <h2 className="section-headline">
              {t("landing.h1a")}
              <br />
              {t("landing.h1b")}.
            </h2>
            <div className="section-body">
              <p>{t("landing.b1a")}</p>
              <p>{t("landing.b1b")}</p>
            </div>
          </div>
        </div>
        <div className="section-rule" />
      </section>

      <section className="landing-section" id="process">
        <div className="section-inner">
          <div className="section-kick">{t("landing.k2")}</div>
          <h2 className="section-headline">
            {t("landing.h2a")}
            <br />
            {t("landing.h2b")}
          </h2>
          <div className="spreads-grid">
            <div className="spread">
              <div className="spread-num">I</div>
              <h3 className="spread-title">{t("landing.s1t")}</h3>
              <div className="spread-rule" />
              <p className="spread-body">{t("landing.s1b")}</p>
            </div>
            <div className="spread">
              <div className="spread-num">II</div>
              <h3 className="spread-title">{t("landing.s2t")}</h3>
              <div className="spread-rule" />
              <p className="spread-body">{t("landing.s2b")}</p>
            </div>
            <div className="spread">
              <div className="spread-num">III</div>
              <h3 className="spread-title">{t("landing.s3t")}</h3>
              <div className="spread-rule" />
              <p className="spread-body">{t("landing.s3b")}</p>
            </div>
          </div>
        </div>
        <div className="section-rule" />
      </section>

      <section className="landing-section" id="features">
        <div className="section-inner">
          <div className="section-kick">{t("landing.k3")}</div>
          <h2 className="section-headline">
            {t("landing.h3a")}
            <br />
            {t("landing.h3b")}
          </h2>
          <div className="feature-list">
            {features.map(([label, desc], i) => (
              <div
                className="feature-row"
                key={i}
                style={{ transitionDelay: `${i * 0.07}s` }}
              >
                <span className="feature-label">{label}</span>
                <span className="feature-desc">{desc}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="section-rule" />
      </section>

      <section className="landing-section landing-cta" id="start">
        <div className="section-inner">
          <div className="section-kick">{t("landing.k4")}</div>
          <h2 className="cta-headline">
            {t("landing.h4a")}
            <br />
            {t("landing.h4b")}
          </h2>
          <div className="cta-actions">
            {user ? (
              <button
                className="cta-button"
                type="button"
                onClick={() => navigate("/dashboard")}
              >
                {t("landing.ctaDash")}
              </button>
            ) : (
              <>
                <button
                  className="cta-button"
                  type="button"
                  onClick={onLoginClick}
                >
                  {t("landing.ctaIn")}
                </button>
                <button
                  className="cta-button cta-button-outline"
                  type="button"
                  onClick={onRegisterClick}
                >
                  {t("landing.ctaUp")}
                </button>
                <p className="cta-note">{t("landing.ctaNote")}</p>
              </>
            )}
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="footer-inner">
          <span className="footer-mark">GQ</span>
          <span className="footer-text">{t("landing.footTxt")}</span>
          <span className="footer-year">{new Date().getFullYear()}</span>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
