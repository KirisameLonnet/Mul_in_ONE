import { createI18n } from 'vue-i18n'

const STORAGE_KEY = 'mio-locale'

const getDefaultLocale = () => {
  if (typeof localStorage !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return saved
  }
  if (typeof navigator !== 'undefined') {
    const lang = navigator.language.toLowerCase()
    if (lang.startsWith('zh')) return 'zh'
  }
  return 'en'
}

export const availableLocales = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh' }
]

export const messages = {
  en: {
    common: {
      appName: 'Mul-in-ONE',
      appSubtitle: 'Multi-Agent Social Chat',
      language: 'Language',
      english: 'English',
      chinese: '中文',
      cancel: 'Cancel',
      save: 'Save',
      delete: 'Delete',
      create: 'Create',
      edit: 'Edit',
      back: 'Back',
      close: 'Close',
      retry: 'Retry',
      refresh: 'Refresh',
      confirm: 'Confirm',
      continue: 'Continue',
      loading: 'Loading...',
      required: 'Field is required',
      optional: 'optional',
      actions: 'Actions',
      search: 'Search',
      notSet: 'Not set',
      pending: 'Pending',
      verified: 'Verified',
      active: 'Active',
      inactive: 'Inactive',
      success: 'Success',
      failed: 'Failed'
    },
    nav: {
      menu: 'Menu',
      sessions: 'Sessions',
      personas: 'Personas',
      profiles: 'API Profiles',
      account: 'Account Settings',
      adminUsers: 'Admin Users',
      debug: 'DEBUG',
      logout: 'Logout',
      user: 'User: {username}'
    },
    layout: {
      title: 'MIO Dashboard',
      verifyBanner: 'Email not verified: please click the verification link in your inbox before performing write actions. You can resend it from Account Settings.',
      goVerify: 'Verify now',
      verifyNotify: 'Please verify your email before continuing'
    },
    language: {
      label: 'Language',
      placeholder: 'Select language'
    },
    login: {
      title: 'Mul-in-ONE',
      subtitle: 'Multi-Agent Social Chat',
      description: 'Enter your username to start chatting with multiple AI personas.',
      usernamePlaceholder: 'Enter your username',
      enterApp: 'Enter App',
      email: 'Email',
      password: 'Password',
      signIn: 'Sign In',
      thirdParty: 'Third-party Login',
      gitee: 'Gitee',
      github: 'GitHub',
      noAccount: "Don't have an account?",
      goRegister: 'Register',
      rules: {
        email: 'Please enter your email',
        password: 'Please enter your password'
      },
      welcomeBack: 'Welcome back, {name}!',
      loginFailed: 'Login failed, please check your email and password',
      oauthFailed: 'OAuth login failed',
      alphaDialog: {
        title: 'Heads up: alpha build',
        message: 'MIO is currently in alpha. The demo database may be wiped at any time—avoid storing sensitive data. Source code: {repo}. If you like the project, please star it and report issues/bugs on GitHub.',
        ok: 'Got it',
        skip: 'Skip for now'
      }
    },
    register: {
      title: 'Create Account',
      subtitle: 'Join Mul-in-ONE',
      username: 'Username',
      email: 'Email',
      password: 'Password',
      confirmPassword: 'Confirm Password',
      displayName: 'Display Name (optional)',
      submit: 'Register',
      haveAccount: 'Already have an account?',
      goLogin: 'Log in now',
      rules: {
        usernameRequired: 'Please enter username',
        usernameLength: 'Username must be at least 3 characters',
        emailRequired: 'Please enter email',
        emailValid: 'Please enter a valid email address',
        passwordRequired: 'Please enter password',
        passwordLength: 'Password must be at least 6 characters',
        confirmRequired: 'Please confirm password',
        confirmMatch: 'Passwords do not match'
      },
      success: 'Registration successful! Please check your email and verify before logging in.',
      failed: 'Registration failed, please try again later'
    },
    verifyEmail: {
      pendingHint: 'Didn\'t receive it? Check your spam folder or click the "Verify Email" button in the email.',
      loginNow: 'Log in now',
      backToRegister: 'Back to register',
      iVerified: 'I have completed verification',
      resend: 'Resend verification email',
      resendCooldown: 'Resend ({seconds}s)',
      resendSending: 'Sending...',
      titleVerifying: 'Verifying...',
      msgVerifying: 'Please wait while we verify your email',
      titleNeedVerify: 'Verify your email',
      msgSentWithEmail: 'We\'ve sent a verification email to {email}. Please click the link to activate your account.',
      msgSent: 'We\'ve sent a verification email. Please click the link to activate your account.',
      titleSuccess: 'Verified!',
      msgSuccess: 'Your email has been verified. You can log in now.',
      titleFailed: 'Verification failed',
      msgFailed: 'Verification token is invalid or expired',
      resendFailedMissingEmail: 'Email address missing, please register again',
      resendSuccess: 'Verification email resent, please check your inbox',
      resendFailed: 'Failed to send, please try again later'
    },
    sessionsPage: {
      title: 'Sessions',
      new: 'New Session',
      loading: 'Loading sessions...',
      searchPlaceholder: 'Search sessions...',
      deleteSelected: 'Delete ({count})',
      listCreated: 'Created: {time}',
      empty: 'No sessions found.',
      createDialog: {
        title: 'Create New Session',
        sessionTitle: 'Session Title (optional)',
        displayName: 'Your display name (optional)',
        handle: 'Your handle (optional)',
        persona: 'Describe yourself (optional)',
        personaPlaceholder: 'Help agents understand who you are...',
        personaHint: 'This helps agents understand your role in the conversation',
        cancel: 'Cancel',
        create: 'Create'
      },
      editDialog: {
        title: 'Edit Session Detail',
        cancel: 'Cancel',
        save: 'Save'
      },
      deleteDialog: {
        title: 'Delete Session',
        body: 'Are you sure you want to delete this session? This action cannot be undone.',
        delete: 'Delete'
      },
      batchDeleteDialog: {
        title: 'Delete Sessions',
        body: 'Are you sure you want to delete {count} sessions? This action cannot be undone.',
        delete: 'Delete All'
      },
      tooltips: {
        edit: 'Edit Session Detail',
        delete: 'Delete Session'
      },
      notify: {
        loadFailed: 'Failed to load sessions',
        createFailed: 'Failed to create session',
        updateSuccess: 'Session updated successfully',
        updateFailed: 'Failed to update session',
        deleteSuccess: 'Session deleted successfully',
        deleteFailed: 'Failed to delete session',
        batchDeleteSuccess: 'Sessions deleted successfully',
        batchDeleteFailed: 'Failed to delete sessions'
      }
    },
    sessionManager: {
      title: 'Sessions',
      new: 'New Session',
      loading: 'Loading sessions...',
      created: 'Created: {time}',
      back: 'Back',
      chatTitle: 'Session #{id}',
      targetPersonas: 'Target Personas:',
      inputPlaceholder: 'Type a message...',
      errors: {
        create: 'Failed to create session',
        send: 'Failed to send message'
      }
    },
    personas: {
      title: 'Personas',
      buildVectorDb: 'Build Vector Database',
      new: 'New Persona',
      embeddingConfigTitle: 'Global Embedding Model Configuration',
      embeddingConfigDesc: 'Configure an embedding model to enable persona background (RAG). This applies to all personas.',
      embeddingProfile: 'Embedding API Profile',
      embeddingProfileHint: 'Only embedding-capable API Profiles are shown',
      actualEmbeddingDim: 'Actual dimension',
      actualEmbeddingDimHint: 'Leave empty to use maximum dimension',
      saveConfig: 'Save configuration',
      currentModel: 'Current model',
      listTitle: 'Existing Personas',
      placeholders: {
        name: 'e.g. Coding Assistant',
        handle: 'e.g. coder',
        tone: 'e.g. professional',
        prompt: 'Enter system prompt...',
        apiProfile: 'Select API Profile'
      },
      columns: {
        avatar: 'Avatar',
        id: 'ID',
        name: 'Name',
        handle: 'Handle',
        tone: 'Tone',
        proactivity: 'Proactivity',
        apiProfile: 'API Profile',
        actions: 'Actions'
      },
      createDialog: {
        title: 'Create New Persona',
        avatar: 'Avatar',
        name: 'Name',
        handle: 'Handle',
        tone: 'Tone',
        proactivity: 'Proactivity (0-1)',
        memoryWindow: 'Memory Window (-1 = Unlimited)',
        maxAgents: 'Max Agents/Turn (-1 = Unlimited)',
        apiProfile: 'API Profile',
        background: 'Background / Biography (any length)',
        prompt: 'System Prompt',
        isDefault: 'Set as Default',
        cancel: 'Cancel',
        create: 'Create'
      },
      editDialog: {
        title: 'Edit Persona',
        currentAvatarPath: 'Current avatar path',
        avatarHint: 'Avatar path is generated after upload and cannot be edited manually',
        save: 'Save'
      },
      deleteDialog: {
        title: 'Delete Persona',
        body: 'Are you sure you want to delete "{name}"?'
      },
      avatarDialog: {
        title: 'Avatar Upload & Apply',
        saveFirst: 'Save the persona before uploading an avatar. You can fill the URL first, save, then upload.',
        cropPlaceholder: 'Select an avatar file to crop',
        scale: 'Scale',
        reset: 'Reset',
        tips: 'Recommended 1:1 PNG/JPG/WEBP · ≤2MB\nUpload endpoint `/api/personas/personas/{id}/avatar`',
        chooseFile: 'Choose avatar file',
        currentPath: 'Current path:',
        cancel: 'Cancel',
        upload: 'Upload & Apply'
      },
      buildDialog: {
        title: 'Building vector database',
        description: 'Generating vector index for all persona backgrounds...'
      },
      notifications: {
        loadFailed: 'Failed to load data',
        saveEmbeddingSuccess: 'Embedding configuration saved',
        saveEmbeddingFailed: 'Failed to save embedding configuration',
        savePersonaFailed: 'Failed to save persona',
        createSuccess: 'Persona created',
        updateSuccess: 'Persona updated',
        deleteFailed: 'Failed to delete persona',
        deleteSuccess: 'Persona deleted',
        avatarNeedSave: 'Please save the persona before uploading an avatar',
        avatarNeedFile: 'Please choose an avatar file',
        avatarUploaded: 'Avatar uploaded and applied',
        avatarUploadFailed: 'Failed to upload avatar',
        avatarMissing: 'No avatar to crop',
        canvasUnavailable: 'Canvas unavailable',
        generateAvatarFailed: 'Failed to generate avatar',
        buildNeedEmbedding: 'Please configure an embedding model first',
        buildError: 'Error building vector database',
        buildCompleteWithErrors: 'Completed with {count} errors',
        buildComplete: 'Vector database built successfully',
        buildCaption: 'Processed {processed} personas, {docs} documents',
        buildErrorInfo: 'Check console for detailed error information'
      },
      rag: {
        refreshing: 'Refreshing knowledge base...',
        refreshSuccess: 'Refresh successful! {count} fragments added to {collection}',
        refreshFailed: 'Refresh failed: {message}',
        refreshButton: 'Refresh knowledge base'
      },
      fields: {
        dimensionRange: 'Range: 32-{max}',
        mustBeMinusOneOr: 'Must be -1 or ≥ 1'
      }
    },
    apiProfiles: {
      title: 'API Profiles',
      new: 'New Profile',
      listTitle: 'Existing Profiles',
      columns: {
        id: 'ID',
        name: 'Name',
        baseUrl: 'Base URL',
        model: 'Model',
        apiKeyPreview: 'API Key (Preview)',
        temperature: 'Temperature',
        actions: 'Actions'
      },
      createDialog: {
        title: 'Create New API Profile',
        name: 'Name',
        baseUrl: 'Base URL',
        model: 'Model',
        apiKey: 'API Key',
        temperature: 'Temperature',
        cancel: 'Cancel',
        create: 'Create'
      },
      editDialog: {
        title: 'Edit API Profile',
        apiKey: 'API Key (leave blank to keep)',
        save: 'Save'
      },
      deleteDialog: {
        title: 'Delete API Profile',
        body: 'Are you sure you want to delete "{name}"?'
      },
      embedding: {
        title: 'Embedding Model Configuration',
        supportEmbedding: 'Supports embedding model',
        maxDim: 'Max embedding dimension',
        hint: 'Maximum output dimension supported by the model. Example: 4096 (Qwen3-Embedding-8B), 1536 (OpenAI text-embedding-3-small)',
        dimRange: 'Dimension range: 32-8192',
        tip: 'You can choose a smaller dimension to save storage (e.g. 32-{dim})'
      },
      notify: {
        loadFailed: 'Failed to load profiles',
        createSuccess: 'Profile created',
        createFailed: 'Failed to create profile',
        updateSuccess: 'Profile updated',
        updateFailed: 'Failed to update profile',
        deleteSuccess: 'Profile deleted',
        deleteFailed: 'Failed to delete profile',
        deleteFailedDetail: 'Failed to delete profile: {detail}',
        serverChecking: 'Checking {name} on backend...',
        serverHealthy: 'Healthy: {status}',
        serverFailed: 'Failed: {reason}',
        serverCheckFailed: 'Health check failed: {detail}'
      }
    },
    account: {
      title: 'Account Settings',
      subtitle: 'Manage your profile information and account lifecycle.',
      loadError: 'Failed to load account',
      retry: 'Retry',
      verifyRequiredTitle: 'Email verification required',
      verifyRequiredDesc: 'You must verify your email before creating sessions, personas, or API profiles. Please check your inbox and click the link.',
      resend: 'Resend verification email',
      resendCooldown: 'Resend verification email ({seconds}s)',
      resendSending: 'Sending...',
      iveVerified: "I've verified my email",
      profile: 'Profile',
      email: 'Email',
      username: 'Username',
      displayName: 'Display name',
      role: 'Role',
      status: 'Status',
      administrator: 'Administrator',
      user: 'User',
      superuser: 'Superuser',
      standardUser: 'Standard user',
      pending: 'Pending',
      verified: 'Verified',
      active: 'Active',
      inactive: 'Inactive',
      dangerZone: 'Danger Zone',
      dangerDesc: 'Permanently delete your Mul in ONE account.',
      dangerDetail: 'Deleting your account removes all sessions, personas, API profiles, and stored data. This action cannot be undone.',
      deleteAccount: 'Delete Account',
      deleteDialogTitle: 'Confirm Account Deletion',
      deleteDialogBody: 'This will permanently delete your account and all associated data. Please type {keyword} to continue.',
      deleteConfirmPlaceholder: 'Type DELETE to confirm',
      delete: 'Delete',
      notifications: {
        resendMissingEmail: 'Email address missing, please register again',
        resendSuccess: 'Verification email resent, please check your inbox',
        resendFailed: 'Failed to send verification email',
        manualRefreshFailed: 'Failed to refresh verification status',
        manualVerified: 'Email verified! You now have full access.',
        manualPending: 'Still pending. Please check your inbox or resend the link.',
        verifiedRefreshed: 'Email verified! Account data refreshed.',
        deleteSuccess: 'Account deleted. You have been logged out.',
        deleteFailed: 'Failed to delete account'
      }
    },
    admin: {
      title: 'User Administration',
      subtitle: 'Manage all registered accounts',
      noData: 'No users yet',
      columns: {
        id: 'ID',
        username: 'Username',
        email: 'Email',
        role: 'Role',
        permission: 'Permission',
        createdAt: 'Joined At',
        actions: 'Actions'
      },
      badgeAdmin: 'Admin',
      badgeMember: 'Member',
      dialogTitle: 'Delete User',
      dialogBody: 'Delete user {username}? This action cannot be undone.',
      cancel: 'Cancel',
      delete: 'Delete',
      notify: {
        loadFailed: 'Failed to load users',
        cannotRemoveSelf: 'You cannot remove your own admin role',
        updateStatus: 'Updated admin status for {username}',
        deleteSuccess: 'Deleted user {username}',
        updateFailed: 'Failed to update admin status',
        deleteFailed: 'Failed to delete user'
      }
    },
    debug: {
      refresh: 'Refresh',
      autoRefresh: 'Auto refresh',
      options: {
        '200': '200 lines',
        '500': '500 lines',
        '1000': '1000 lines',
        '2000': '2000 lines'
      },
      loadFailed: 'Failed to load logs: {error}'
    },
    languageSwitcher: {
      label: 'Language',
      en: 'English',
      zh: '中文'
    }
  },
  zh: {
    common: {
      appName: 'Mul-in-ONE',
      appSubtitle: '多智能体对话系统',
      language: '语言',
      english: 'English',
      chinese: '中文',
      cancel: '取消',
      save: '保存',
      delete: '删除',
      create: '创建',
      edit: '编辑',
      back: '返回',
      close: '关闭',
      retry: '重试',
      refresh: '刷新',
      confirm: '确认',
      continue: '继续',
      loading: '加载中...',
      required: '必填项',
      optional: '可选',
      actions: '操作',
      search: '搜索',
      notSet: '未设置',
      pending: '待验证',
      verified: '已验证',
      active: '启用',
      inactive: '停用',
      success: '成功',
      failed: '失败'
    },
    nav: {
      menu: '菜单',
      sessions: '会话',
      personas: '人物',
      profiles: 'API 配置',
      account: '账号设置',
      adminUsers: '用户管理',
      debug: '调试',
      logout: '退出登录',
      user: '用户：{username}'
    },
    layout: {
      title: 'MIO 控制台',
      verifyBanner: '邮箱未验证：请前往邮箱点击验证链接后再继续使用写操作。可在 Account Settings 页面重新发送邮件。',
      goVerify: '去验证',
      verifyNotify: '请先完成邮箱验证后再执行此操作'
    },
    language: {
      label: '语言',
      placeholder: '选择语言'
    },
    login: {
      title: 'Mul-in-ONE',
      subtitle: '多智能体对话系统',
      description: '输入用户名即可与多个 AI 角色聊天。',
      usernamePlaceholder: '输入用户名',
      enterApp: '进入应用',
      email: '邮箱',
      password: '密码',
      signIn: '登录',
      thirdParty: '第三方登录',
      gitee: 'Gitee',
      github: 'GitHub',
      noAccount: '还没有账号？',
      goRegister: '注册',
      rules: {
        email: '请输入邮箱',
        password: '请输入密码'
      },
      welcomeBack: '欢迎回来，{name}！',
      loginFailed: '登录失败，请检查邮箱和密码',
      oauthFailed: 'OAuth 登录失败',
      alphaDialog: {
        title: '提示：Alpha 版本',
        message: '当前为 Alpha 版本，演示数据库可能随时清空，请勿存放敏感数据。源代码：{repo}。如果觉得有用欢迎点 Star，有问题或 Bug 请到 GitHub Issue 反馈。',
        ok: '知道了',
        skip: '稍后再说'
      }
    },
    register: {
      title: '创建账号',
      subtitle: '加入 Mul-in-ONE',
      username: '用户名',
      email: '邮箱',
      password: '密码',
      confirmPassword: '确认密码',
      displayName: '显示名称（可选）',
      submit: '注册',
      haveAccount: '已有账号？',
      goLogin: '立即登录',
      rules: {
        usernameRequired: '请输入用户名',
        usernameLength: '用户名至少3个字符',
        emailRequired: '请输入邮箱',
        emailValid: '请输入有效的邮箱地址',
        passwordRequired: '请输入密码',
        passwordLength: '密码至少6个字符',
        confirmRequired: '请确认密码',
        confirmMatch: '两次密码输入不一致'
      },
      success: '注册成功！请检查邮箱并完成验证后再登录。',
      failed: '注册失败，请稍后重试'
    },
    verifyEmail: {
      pendingHint: '没收到？请检查垃圾邮箱或点击验证邮件中的「Verify Email」按钮。',
      loginNow: '立即登录',
      backToRegister: '返回注册',
      iVerified: '我已完成验证',
      resend: '重新发送验证邮件',
      resendCooldown: '重新发送 ({seconds}s)',
      resendSending: '发送中...',
      titleVerifying: '验证中...',
      msgVerifying: '请稍候，正在验证你的邮箱',
      titleNeedVerify: '验证你的邮箱',
      msgSentWithEmail: '我们已经将验证邮件发送至 {email}，请点击邮件中的链接完成激活。',
      msgSent: '我们已经将验证邮件发送至你的邮箱，请点击邮件中的链接完成激活。',
      titleSuccess: '验证成功！',
      msgSuccess: '你的邮箱已验证，现在可以登录使用了',
      titleFailed: '验证失败',
      msgFailed: '验证令牌无效或已过期',
      resendFailedMissingEmail: '无法确定邮箱地址，请返回重新注册',
      resendSuccess: '验证邮件已重新发送，请查收',
      resendFailed: '发送失败，请稍后重试'
    },
    sessionsPage: {
      title: '会话',
      new: '新建会话',
      loading: '正在加载会话...',
      searchPlaceholder: '搜索会话...',
      deleteSelected: '删除（{count}）',
      listCreated: '创建时间：{time}',
      empty: '暂无会话',
      createDialog: {
        title: '创建新会话',
        sessionTitle: '会话标题（可选）',
        displayName: '你的显示名称（可选）',
        handle: '你的 Handle（可选）',
        persona: '描述你自己（可选）',
        personaPlaceholder: '让智能体更了解你的角色...',
        personaHint: '帮助智能体理解你的角色定位',
        cancel: '取消',
        create: '创建'
      },
      editDialog: {
        title: '编辑会话详情',
        cancel: '取消',
        save: '保存'
      },
      deleteDialog: {
        title: '删除会话',
        body: '确定删除该会话？此操作不可恢复。',
        delete: '删除'
      },
      batchDeleteDialog: {
        title: '批量删除会话',
        body: '确定删除 {count} 个会话？此操作不可恢复。',
        delete: '全部删除'
      },
      tooltips: {
        edit: '编辑会话详情',
        delete: '删除会话'
      },
      notify: {
        loadFailed: '加载会话失败',
        createFailed: '创建会话失败',
        updateSuccess: '会话更新成功',
        updateFailed: '更新会话失败',
        deleteSuccess: '删除会话成功',
        deleteFailed: '删除会话失败',
        batchDeleteSuccess: '批量删除成功',
        batchDeleteFailed: '批量删除失败'
      }
    },
    sessionManager: {
      title: '会话',
      new: '新会话',
      loading: '正在加载会话...',
      created: '创建时间：{time}',
      back: '返回',
      chatTitle: '会话 #{id}',
      targetPersonas: '目标人物：',
      inputPlaceholder: '输入消息...',
      errors: {
        create: '创建会话失败',
        send: '发送消息失败'
      }
    },
    personas: {
      title: '人物',
      buildVectorDb: '构建向量数据库',
      new: '新建人物',
      embeddingConfigTitle: '全局 Embedding 模型配置',
      embeddingConfigDesc: '使用人物背景传记（RAG）需要配置一个 Embedding 模型。此配置对所有 Persona 生效。',
      embeddingProfile: 'Embedding API Profile',
      embeddingProfileHint: '只显示标记为 Embedding 模型的 API Profile',
      actualEmbeddingDim: '实际使用维度',
      actualEmbeddingDimHint: '留空使用最大维度',
      saveConfig: '保存配置',
      currentModel: '当前模型',
      listTitle: '已有 Persona',
      placeholders: {
        name: '例如：Coding Assistant',
        handle: '例如：coder',
        tone: '例如：professional',
        prompt: '输入系统提示...',
        apiProfile: '选择 API Profile'
      },
      columns: {
        avatar: '头像',
        id: 'ID',
        name: '名称',
        handle: 'Handle',
        tone: '语气',
        proactivity: '主动性',
        apiProfile: 'API 配置',
        actions: '操作'
      },
      createDialog: {
        title: '创建新 Persona',
        avatar: '头像',
        name: '名称',
        handle: 'Handle',
        tone: '语气',
        proactivity: '主动性 (0-1)',
        memoryWindow: '记忆窗口 (-1 = 不限)',
        maxAgents: '每轮最多智能体 (-1 = 不限)',
        apiProfile: 'API 配置',
        background: '背景/传记（任意长度）',
        prompt: '系统提示',
        isDefault: '设为默认',
        cancel: '取消',
        create: '创建'
      },
      editDialog: {
        title: '编辑 Persona',
        currentAvatarPath: '当前头像路径',
        avatarHint: '头像路径由上传生成，不支持手动填写',
        save: '保存'
      },
      deleteDialog: {
        title: '删除 Persona',
        body: '确定删除 “{name}” 吗？'
      },
      avatarDialog: {
        title: '头像上传与应用',
        saveFirst: '保存 Persona 后才能上传头像。创建时可先填写头像 URL，保存后再上传文件。',
        cropPlaceholder: '选择头像文件后进行裁切',
        scale: '缩放',
        reset: '重置',
        tips: '推荐 1:1 PNG/JPG/WEBP · ≤2MB\n上传接口 `/api/personas/personas/{id}/avatar`',
        chooseFile: '选择头像文件',
        currentPath: '当前路径：',
        cancel: '取消',
        upload: '上传并应用'
      },
      buildDialog: {
        title: '正在构建向量数据库',
        description: '正在为所有 Persona 的背景资料生成向量索引...'
      },
      notifications: {
        loadFailed: '数据加载失败',
        saveEmbeddingSuccess: 'Embedding 配置已保存',
        saveEmbeddingFailed: '保存配置失败',
        savePersonaFailed: '保存 Persona 失败',
        createSuccess: '创建 Persona 成功',
        updateSuccess: '更新 Persona 成功',
        deleteFailed: '删除 Persona 失败',
        deleteSuccess: '删除 Persona 成功',
        avatarNeedSave: '请先保存 Persona 后再上传头像',
        avatarNeedFile: '请选择头像文件',
        avatarUploaded: '头像已上传并应用',
        avatarUploadFailed: '上传头像失败',
        avatarMissing: '没有可裁剪的头像',
        canvasUnavailable: 'Canvas 不可用',
        generateAvatarFailed: '生成头像失败',
        buildNeedEmbedding: '请先配置 Embedding 模型',
        buildError: '构建向量数据库时发生错误',
        buildCompleteWithErrors: '完成，但有 {count} 个错误',
        buildComplete: '向量数据库构建成功',
        buildCaption: '处理了 {processed} 个 Persona，共 {docs} 个文档',
        buildErrorInfo: '查看控制台以获取详细错误信息'
      },
      rag: {
        refreshing: '刷新资料库中...',
        refreshSuccess: '成功刷新！摄取了 {count} 个文档片段到 {collection}',
        refreshFailed: '刷新失败：{message}',
        refreshButton: '刷新资料库'
      },
      fields: {
        dimensionRange: '范围：32-{max}',
        mustBeMinusOneOr: '必须为 -1 或 ≥ 1'
      }
    },
    apiProfiles: {
      title: 'API Profiles',
      new: '新建配置',
      listTitle: '已有配置',
      columns: {
        id: 'ID',
        name: '名称',
        baseUrl: 'Base URL',
        model: '模型',
        apiKeyPreview: 'API Key（预览）',
        temperature: '温度',
        actions: '操作'
      },
      createDialog: {
        title: '创建 API Profile',
        name: '名称',
        baseUrl: 'Base URL',
        model: '模型',
        apiKey: 'API Key',
        temperature: '温度',
        cancel: '取消',
        create: '创建'
      },
      editDialog: {
        title: '编辑 API Profile',
        apiKey: 'API Key（留空则不变）',
        save: '保存'
      },
      deleteDialog: {
        title: '删除 API Profile',
        body: '确定删除 “{name}” 吗？'
      },
      embedding: {
        title: 'Embedding 模型配置',
        supportEmbedding: '支持 Embedding 模型',
        maxDim: '最大 Embedding 维度',
        hint: '模型支持的最大输出维度。例如：4096（Qwen3-Embedding-8B），1536（OpenAI text-embedding-3-small）',
        dimRange: '维度范围：32-8192',
        tip: '实际使用时可以指定更小的维度以节省存储空间（如 32-{dim}）'
      },
      notify: {
        loadFailed: '加载配置失败',
        createSuccess: '创建成功',
        createFailed: '创建失败',
        updateSuccess: '更新成功',
        updateFailed: '更新失败',
        deleteSuccess: '删除成功',
        deleteFailed: '删除失败',
        deleteFailedDetail: '删除失败：{detail}',
        serverChecking: '正在后端检查 {name}...',
        serverHealthy: '健康: {status}',
        serverFailed: '失败: {reason}',
        serverCheckFailed: '检查失败: {detail}'
      }
    },
    account: {
      title: '账号设置',
      subtitle: '管理个人信息与账号生命周期。',
      loadError: '获取账号信息失败',
      retry: '重试',
      verifyRequiredTitle: '需要邮箱验证',
      verifyRequiredDesc: '完成邮箱验证后才能创建会话、人物或 API 配置。请查收邮件并点击链接。',
      resend: '重新发送验证邮件',
      resendCooldown: '重新发送验证邮件（{seconds} 秒）',
      resendSending: '发送中...',
      iveVerified: '我已完成验证',
      profile: '个人信息',
      email: '邮箱',
      username: '用户名',
      displayName: '显示名称',
      role: '角色',
      status: '状态',
      administrator: '管理员',
      user: '用户',
      superuser: '超级用户',
      standardUser: '普通用户',
      pending: '待验证',
      verified: '已验证',
      active: '启用',
      inactive: '停用',
      dangerZone: '危险操作',
      dangerDesc: '永久删除你的 Mul in ONE 账号。',
      dangerDetail: '删除账号将移除所有会话、Persona、API 配置及存储数据，此操作不可恢复。',
      deleteAccount: '删除账号',
      deleteDialogTitle: '确认删除账号',
      deleteDialogBody: '此操作会永久删除账号及数据，请输入 {keyword} 以继续。',
      deleteConfirmPlaceholder: '输入 DELETE 进行确认',
      delete: '删除',
      notifications: {
        resendMissingEmail: '无法确定邮箱地址，请重新注册',
        resendSuccess: '验证邮件已重新发送，请查收',
        resendFailed: '发送验证邮件失败',
        manualRefreshFailed: '刷新验证状态失败',
        manualVerified: '邮箱验证成功，现在拥有全部权限。',
        manualPending: '仍在等待验证，请检查邮箱或重新发送链接。',
        verifiedRefreshed: '邮箱验证成功，账号数据已刷新。',
        deleteSuccess: '账号已删除，已退出登录',
        deleteFailed: '删除账号失败'
      }
    },
    admin: {
      title: '用户管理',
      subtitle: '管理所有注册账号',
      noData: '暂无用户',
      columns: {
        id: 'ID',
        username: '用户名',
        email: '邮箱',
        role: '角色',
        permission: '权限',
        createdAt: '注册时间',
        actions: '操作'
      },
      badgeAdmin: '管理员',
      badgeMember: '成员',
      dialogTitle: '删除用户',
      dialogBody: '确定删除用户 {username}？该操作不可撤销。',
      cancel: '取消',
      delete: '删除',
      notify: {
        loadFailed: '获取用户列表失败',
        cannotRemoveSelf: '不能取消自己的管理员权限',
        updateStatus: '已更新 {username} 的管理员权限',
        deleteSuccess: '已删除用户 {username}',
        updateFailed: '更新管理员权限失败',
        deleteFailed: '删除用户失败'
      }
    },
    debug: {
      refresh: '刷新',
      autoRefresh: '自动刷新',
      options: {
        '200': '200 行',
        '500': '500 行',
        '1000': '1000 行',
        '2000': '2000 行'
      },
      loadFailed: '获取日志失败: {error}'
    },
    languageSwitcher: {
      label: '语言',
      en: 'English',
      zh: '中文'
    }
  }
}

export const i18n = createI18n({
  legacy: false,
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  globalInjection: true,
  messages
})

export function setLocale(locale: string) {
  i18n.global.locale.value = locale
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, locale)
  }
}

export type LocaleKey = keyof typeof messages
