import asyncio

async def detect_ad_slots(page):
    """
    Analyzes the page DOM to detect advertisement containers.
    Returns a list of dictionaries with x, y, width, height, and selector.
    """
    try:
        # We use page.evaluate to run high-performance DOM traversal in JS
        ad_slots = await page.evaluate("""
            () => {
                const results = [];
                const adSignatures = [
                    'ins.adsbygoogle',
                    '[id^="google_ads_iframe"]',
                    '[id^="div-gpt-ad"]',
                    '[class*="ad-unit"]',
                    '[id*="ad-unit"]',
                    '[class*="sponsored-post"]',
                    '.ad-container',
                    '.ad-slot',
                    '.trc_rbox_container', // Taboola
                    '.outbrain',
                    'iframe[src*="doubleclick.net"]',
                    'iframe[src*="googlesyndication.com"]',
                    'iframe[id^="ads-"]'
                ];

                // 1. Check common signatures
                const candidates = document.querySelectorAll(adSignatures.join(', '));
                
                candidates.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    
                    // Filter: Must be visible and have reasonable dimensions
                    if (rect.width > 10 && rect.height > 10 && rect.top >= 0) {
                        results.push({
                            x: Math.round(rect.left + window.scrollX),
                            y: Math.round(rect.top + window.scrollY),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            selector: el.tagName.toLowerCase() + (el.className ? '.' + el.className.split(' ').join('.') : '')
                        });
                    }
                });

                // 2. Generic iFrame check (potential ads not caught by signatures)
                const iframes = document.querySelectorAll('iframe');
                iframes.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const src = el.src || '';
                    
                    // Only add if not already caught and looks like an ad source
                    const looksLikeAd = src.includes('ads') || src.includes('pixel') || src.includes('track');
                    
                    if (looksLikeAd && rect.width > 50 && rect.height > 50) {
                        const exists = results.some(r => Math.abs(r.x - (rect.left + window.scrollX)) < 5);
                        if (!exists) {
                            results.push({
                                x: Math.round(rect.left + window.scrollX),
                                y: Math.round(rect.top + window.scrollY),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height),
                                selector: 'iframe (src-match)'
                            });
                        }
                    }
                });

                return results;
            }
        """)

        # Print to terminal for debugging
        if ad_slots:
            print(f"\n[AD-DETECTOR] Detected {len(ad_slots)} potential ad slots:")
            for i, slot in enumerate(ad_slots):
                print(f"  {i+1}. {slot['width']}x{slot['height']} at ({slot['x']}, {slot['y']})")
        else:
            print("[AD-DETECTOR] No ad slots found.")

        return ad_slots

    except Exception as e:
        print(f"[AD-DETECTOR] Error during detection: {e}")
        return []
