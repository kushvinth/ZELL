function useVisible(delay = 0) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setVisible(true), delay);
    return () => window.clearTimeout(timer);
  }, [delay]);

  return visible;
}

function useClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return now;
}

function useCountUp(target, duration = 1100) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const finalValue = safeNumber(target, 0);
    const start = performance.now();
    let raf = 0;

    const tick = (time) => {
      const progress = Math.min((time - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(finalValue * eased));
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}

function useStepper(totalSteps, intervalMs = 1400) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!safeNumber(totalSteps)) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setStep((prev) => {
        if (prev >= totalSteps - 1) {
          return totalSteps - 1;
        }
        return prev + 1;
      });
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [totalSteps, intervalMs]);

  return step;
}
