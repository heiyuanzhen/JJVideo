/**
 * 快速页面切换系统
 * 解决页面切换延迟高的问题
 */

(function() {
    'use strict';

    // 配置
    const CONFIG = {
        transitionDuration: 300,  // 过渡动画时长(ms)
        cacheEnabled: true,       // 是否启用页面缓存
        preloadEnabled: true,     // 是否启用预加载
        maxCacheSize: 10          // 最大缓存页面数
    };

    // 页面缓存
    const pageCache = new Map();
    
    // 预加载队列
    const preloadQueue = new Set();

    // 当前正在加载的页面
    let currentLoading = null;

    /**
     * 初始化页面切换系统
     */
    function init() {
        console.log('====== page transition init ======');

        // 拦截所有链接点击
        document.addEventListener('click', handleLinkClick, true);
        
        // 监听浏览器后退/前进
        window.addEventListener('popstate', handlePopState);
        
        // 预加载常用页面
        preloadCommonPages();
    }

    /**
     * 处理链接点击
     */
    function handleLinkClick(e) {
        const link = e.target.closest('a');
        
        if (!link) return;
        if (link.target === '_blank') return;
        if (link.hasAttribute('download')) return;
        
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
        if (href.startsWith('http') && !href.includes(window.location.host)) return;
        
        // 拦截点击，使用AJAX加载
        e.preventDefault();
        e.stopPropagation();
        
        navigateTo(href);
    }

    /**
     * 导航到指定页面
     */
    async function navigateTo(url) {
        // 如果正在加载相同页面，跳过
        if (currentLoading === url) return;
        
        currentLoading = url;
        
        try {
            // 显示加载动画
            showLoadingOverlay();
            
            // 从缓存或网络获取页面
            const html = await fetchPage(url);
            
            // 开始过渡动画
            await transitionOut();
            
            // 更新页面内容
            updatePageContent(html);
            
            // 更新浏览器历史
            window.history.pushState({ url }, '', url);
            
            // 过渡动画结束
            await transitionIn();
            
            // 隐藏加载动画
            hideLoadingOverlay();
            
            // 执行页面初始化脚本
            initializePage();
            
            // 预加载相关页面
            preloadRelatedPages();
            
        } catch (error) {
            console.error('页面加载失败:', error);
            // 失败时使用传统方式加载
            window.location.href = url;
        } finally {
            currentLoading = null;
        }
    }

    /**
     * 获取页面内容
     */
    async function fetchPage(url) {
        // 检查缓存
        if (CONFIG.cacheEnabled && pageCache.has(url)) {
            console.log('📦 从缓存加载:', url);
            return pageCache.get(url);
        }
        
        console.log('🌐 从网络加载:', url);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const html = await response.text();
        
        // 存入缓存
        if (CONFIG.cacheEnabled) {
            cacheCleanup();
            pageCache.set(url, html);
        }
        
        return html;
    }

    /**
     * 显示加载覆盖层
     */
    function showLoadingOverlay() {
        let overlay = document.getElementById('page-transition-overlay');
        
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'page-transition-overlay';
            overlay.innerHTML = `
                <style>
                    #page-transition-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(26, 29, 46, 0.95);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 9999;
                        opacity: 0;
                        transition: opacity 0.3s ease;
                    }
                    #page-transition-overlay.show {
                        opacity: 1;
                    }
                    .transition-spinner {
                        width: 50px;
                        height: 50px;
                        border: 3px solid rgba(102, 126, 234, 0.2);
                        border-top-color: #667eea;
                        border-radius: 50%;
                        animation: spin 0.8s linear infinite;
                    }
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                    .transition-text {
                        color: #667eea;
                        font-size: 14px;
                        margin-top: 15px;
                        text-align: center;
                    }
                </style>
                <div>
                    <div class="transition-spinner"></div>
                    <div class="transition-text">正在切换...</div>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        
        // 触发重排
        overlay.offsetHeight;
        overlay.classList.add('show');
    }

    /**
     * 隐藏加载覆盖层
     */
    function hideLoadingOverlay() {
        const overlay = document.getElementById('page-transition-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }

    /**
     * 过渡动画 - 淡出
     */
    async function transitionOut() {
        const content = document.querySelector('body');
        if (content) {
            content.style.opacity = '1';
            content.style.transition = 'opacity 0.2s ease';
            content.offsetHeight; // 触发重排
            content.style.opacity = '0.3';
            await sleep(200);
        }
    }

    /**
     * 过渡动画 - 淡入
     */
    async function transitionIn() {
        const content = document.querySelector('body');
        if (content) {
            content.style.opacity = '0.3';
            content.offsetHeight; // 触发重排
            content.style.opacity = '1';
            await sleep(200);
            content.style.transition = '';
        }
    }

    /**
     * 更新页面内容
     */
    function updatePageContent(html) {
        // 解析新页面HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // 更新title
        const newTitle = doc.querySelector('title');
        if (newTitle) {
            document.title = newTitle.textContent;
        }
        
        // 更新主体内容
        const newBody = doc.querySelector('body');
        if (newBody) {
            // 保存滚动位置
            const scrollPos = window.scrollY;
            
            // 替换body内容
            document.body.innerHTML = newBody.innerHTML;
            
            // 复制body属性
            Array.from(newBody.attributes).forEach(attr => {
                document.body.setAttribute(attr.name, attr.value);
            });
            
            // 滚动到顶部
            window.scrollTo(0, 0);
        }
    }

    /**
     * 初始化页面
     */
    function initializePage() {
        // 重新初始化Layui
        if (typeof layui !== 'undefined') {
            layui.use(['layer', 'form', 'element'], function() {
                const layer = layui.layer;
                const form = layui.form;
                const element = layui.element;
                form.render();
                element.render();
            });
        }
        
        // 触发自定义事件
        window.dispatchEvent(new Event('pageTransitionComplete'));
    }

    /**
     * 处理浏览器后退/前进
     */
    async function handlePopState(e) {
        if (e.state && e.state.url) {
            await navigateTo(e.state.url);
        }
    }

    /**
     * 预加载常用页面
     */
    function preloadCommonPages() {
        if (!CONFIG.preloadEnabled) return;
        
        const commonPages = [
            '/',
            '/projects',
            '/materials',
            '/settings'
        ];
        
        commonPages.forEach(url => {
            preloadPage(url);
        });
    }

    /**
     * 预加载相关页面
     */
    function preloadRelatedPages() {
        if (!CONFIG.preloadEnabled) return;
        
        // 查找页面中的主要导航链接
        const links = document.querySelectorAll('a[href^="/"]');
        const urls = new Set();
        
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && !href.startsWith('#') && urls.size < 3) {
                urls.add(href);
            }
        });
        
        urls.forEach(url => preloadPage(url));
    }

    /**
     * 预加载单个页面
     */
    async function preloadPage(url) {
        if (pageCache.has(url) || preloadQueue.has(url)) return;
        
        preloadQueue.add(url);
        
        try {
            await fetchPage(url);
            console.log('✅ 预加载成功:', url);
        } catch (error) {
            console.warn('⚠️ 预加载失败:', url);
        } finally {
            preloadQueue.delete(url);
        }
    }

    /**
     * 清理缓存
     */
    function cacheCleanup() {
        if (pageCache.size >= CONFIG.maxCacheSize) {
            // 删除最早的缓存
            const firstKey = pageCache.keys().next().value;
            pageCache.delete(firstKey);
        }
    }

    /**
     * 睡眠函数
     */
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 导出API
    window.PageTransition = {
        navigateTo,
        clearCache: () => pageCache.clear(),
        preloadPage,
        config: CONFIG
    };

})();
