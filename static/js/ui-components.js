/* global window, Vue */
(function () {
    'use strict';

    const { defineComponent, h } = window.__appShared.Vue;
    const { useRouter } = window.__appShared.VueRouter;
    const { statusBadgeType, statusLabel } = window.__appShared;

    // ─────────────────────────────────────────────────────────────────────
    // Page shell: title + optional back button + actions + content wrapper
    // ─────────────────────────────────────────────────────────────────────

    const PageShell = defineComponent({
        props: {
            title: { type: String, default: '' },
            subtitle: { type: String, default: '' },
            showBack: { type: Boolean, default: false },
            backPath: { type: String, default: '' },
        },
        setup(props) {
            const router = useRouter();
            function goBack() {
                if (props.backPath) router.push(props.backPath);
                else router.back();
            }
            return { goBack };
        },
        template: `
            <div class="space-y-6">
                <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div class="flex items-center gap-3">
                        <n-button v-if="showBack" quaternary circle @click="goBack">
                            <template #icon><span>←</span></template>
                        </n-button>
                        <div>
                            <h1 class="text-xl md:text-2xl font-semibold">{{ title }}</h1>
                            <p v-if="subtitle" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{{ subtitle }}</p>
                        </div>
                    </div>
                    <div v-if="$slots.actions" class="flex items-center gap-2">
                        <slot name="actions" />
                    </div>
                </div>
                <slot />
            </div>
        `,
    });

    // ─────────────────────────────────────────────────────────────────────
    // Empty state
    // ─────────────────────────────────────────────────────────────────────

    const EmptyState = defineComponent({
        props: {
            title: { type: String, default: '暂无数据' },
            description: { type: String, default: '' },
            actionText: { type: String, default: '' },
        },
        emits: ['action'],
        setup(props, { emit }) {
            return { emit };
        },
        template: `
            <div class="text-center py-16">
                <div class="text-4xl mb-4">📭</div>
                <h3 class="text-base font-medium text-gray-900 dark:text-gray-100">{{ title }}</h3>
                <p v-if="description" class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ description }}</p>
                <n-button v-if="actionText" class="mt-4" type="primary" @click="$emit('action')">
                    {{ actionText }}
                </n-button>
            </div>
        `,
    });

    // ─────────────────────────────────────────────────────────────────────
    // Loading skeleton
    // ─────────────────────────────────────────────────────────────────────

    const LoadingSkeleton = defineComponent({
        props: {
            type: { type: String, default: 'list' }, // list | card-grid | hero
            rows: { type: Number, default: 4 },
        },
        setup(props) {
            return { props };
        },
        template: `
            <div v-if="type === 'hero'" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <n-skeleton class="aspect-[2/3] max-w-[280px] rounded-lg" />
                    <div class="md:col-span-2 space-y-4">
                        <n-skeleton text :repeat="4" />
                        <n-skeleton height="80px" />
                    </div>
                </div>
                <n-skeleton text :repeat="rows" />
            </div>

            <div v-else-if="type === 'card-grid'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div v-for="i in 6" :key="i" class="p-4 border rounded-lg space-y-3">
                    <div class="flex items-center gap-3">
                        <n-skeleton height="56px" width="56px" />
                        <div class="flex-1">
                            <n-skeleton text :repeat="2" />
                        </div>
                    </div>
                    <n-skeleton height="8px" />
                    <n-skeleton text :repeat="2" />
                </div>
            </div>

            <div v-else class="space-y-3">
                <n-skeleton v-for="i in rows" :key="i" height="48px" />
            </div>
        `,
    });

    // ─────────────────────────────────────────────────────────────────────
    // Error state
    // ─────────────────────────────────────────────────────────────────────

    const ErrorState = defineComponent({
        props: {
            message: { type: String, default: '加载失败' },
            retryText: { type: String, default: '重试' },
        },
        emits: ['retry'],
        template: `
            <div class="text-center py-16">
                <div class="text-4xl mb-4">⚠️</div>
                <h3 class="text-base font-medium text-red-600 dark:text-red-400">{{ message }}</h3>
                <n-button class="mt-4" type="primary" @click="$emit('retry')">
                    {{ retryText }}
                </n-button>
            </div>
        `,
    });

    // ─────────────────────────────────────────────────────────────────────
    // Job status tag
    // ─────────────────────────────────────────────────────────────────────

    const JobStatusTag = defineComponent({
        props: {
            status: { type: String, default: '' },
            size: { type: String, default: 'small' },
        },
        setup(props) {
            return { type: statusBadgeType(props.status), label: statusLabel(props.status) };
        },
        template: `
            <n-tag :type="type" :size="size">{{ label }}</n-tag>
        `,
    });

    // ─────────────────────────────────────────────────────────────────────
    // Breadcrumbs
    // ─────────────────────────────────────────────────────────────────────

    const Breadcrumbs = defineComponent({
        props: {
            items: { type: Array, default: () => [] }, // [{ label, path? }]
        },
        setup(props) {
            const router = useRouter();
            function navigate(path) {
                if (path) router.push(path);
            }
            return { items: props.items, navigate };
        },
        template: `
            <n-breadcrumb class="mb-4">
                <n-breadcrumb-item v-for="(item, idx) in items" :key="idx"
                                   :clickable="!!item.path"
                                   @click="navigate(item.path)">
                    {{ item.label }}
                </n-breadcrumb-item>
            </n-breadcrumb>
        `,
    });

    // Expose
    window.__appShared.PageShell = PageShell;
    window.__appShared.EmptyState = EmptyState;
    window.__appShared.LoadingSkeleton = LoadingSkeleton;
    window.__appShared.ErrorState = ErrorState;
    window.__appShared.JobStatusTag = JobStatusTag;
    window.__appShared.Breadcrumbs = Breadcrumbs;
})();
