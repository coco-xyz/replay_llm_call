# Model Name历史记录功能文档

## 功能概述

在Test Execution页面的Model Name输入框中添加了本地存储历史记录功能，用户之前输入过的模型名称会自动保存，并以下拉列表的形式提供快速选择。

## 功能特性

### 🎯 **核心功能**

#### **1. 自动保存历史**
- ✅ 用户输入模型名称后自动保存到浏览器本地存储
- ✅ 最多保存10个历史记录
- ✅ 新输入的模型名称会移到列表顶部
- ✅ 重复的模型名称不会重复保存

#### **2. 智能下拉显示**
- ✅ 点击输入框时显示历史记录
- ✅ 输入时实时过滤匹配的历史记录
- ✅ 支持模糊搜索（不区分大小写）
- ✅ 点击外部区域自动隐藏下拉列表

#### **3. 便捷操作**
- ✅ 点击历史记录项快速选择
- ✅ 每个历史记录项都有删除按钮（X图标）
- ✅ 支持键盘操作（Enter保存，Escape关闭）
- ✅ 响应式设计，适配不同屏幕尺寸

### 🎨 **用户界面**

#### **输入框增强**
```html
<div class="position-relative">
    <input type="text" class="form-control" id="modelName"
        placeholder="e.g., anthropic/claude-sonnet-4" autocomplete="off">
    <div class="dropdown-menu" id="modelNameDropdown">
        <!-- 历史记录动态生成 -->
    </div>
</div>
```

#### **历史记录项布局**
```
[模型名称                    ] [X]
anthropic/claude-sonnet-4      ❌
google/gemini-2.5-flash        ❌
openai/gpt-4o                  ❌
```

### 🔧 **技术实现**

#### **本地存储管理**
```javascript
// 存储键名
const MODEL_HISTORY_KEY = 'llm_replay_model_history';
const MAX_HISTORY_ITEMS = 10;

// 数据结构
localStorage: {
    "llm_replay_model_history": [
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-flash", 
        "openai/gpt-4o"
    ]
}
```

#### **核心函数**

1. **`setupModelNameInput()`** - 初始化输入框事件监听
2. **`getModelHistory()`** - 从本地存储获取历史记录
3. **`saveModelToHistory(modelName)`** - 保存模型名称到历史
4. **`removeFromModelHistory(modelName)`** - 从历史中删除指定项
5. **`showModelHistory()`** - 显示完整历史记录下拉列表
6. **`filterModelHistory(searchTerm)`** - 根据搜索词过滤历史记录
7. **`hideModelHistory()`** - 隐藏下拉列表

### 📱 **用户交互流程**

#### **1. 首次使用**
```
用户输入模型名称 → 失去焦点/按Enter → 自动保存到历史
```

#### **2. 后续使用**
```
点击输入框 → 显示历史记录 → 点击选择 → 自动填入
```

#### **3. 搜索过滤**
```
输入部分文字 → 实时过滤匹配项 → 显示相关历史记录
```

#### **4. 删除历史**
```
点击历史记录项的X按钮 → 确认删除 → 刷新下拉列表
```

### 🎛️ **事件监听**

#### **输入框事件**
```javascript
// 获得焦点时显示历史
modelNameInput.addEventListener('focus', showModelHistory);

// 输入时过滤历史
modelNameInput.addEventListener('input', function() {
    const value = this.value.trim();
    if (value.length > 0) {
        filterModelHistory(value);
    } else {
        showModelHistory();
    }
});

// 失去焦点时保存并隐藏
modelNameInput.addEventListener('blur', function() {
    const value = this.value.trim();
    if (value) {
        saveModelToHistory(value);
    }
    hideModelHistory();
});
```

#### **键盘事件**
```javascript
modelNameInput.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        // 保存并隐藏
        const value = this.value.trim();
        if (value) saveModelToHistory(value);
        hideModelHistory();
    } else if (event.key === 'Escape') {
        // 直接隐藏
        hideModelHistory();
    }
});
```

#### **全局点击事件**
```javascript
document.addEventListener('click', function(event) {
    if (!modelNameInput.contains(event.target) && 
        !dropdown.contains(event.target)) {
        hideModelHistory();
    }
});
```

### 🎨 **样式设计**

#### **下拉容器样式**
```css
#modelNameDropdown {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 1000;
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
    background-color: white;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    width: 100%;
    max-height: 200px;
    overflow-y: auto;
}
```

#### **历史记录项样式**
```css
.dropdown-item {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #f8f9fa;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
}

.dropdown-item:hover {
    background-color: #f8f9fa;
}
```

#### **删除按钮样式**
```css
.btn-outline-danger {
    border-color: #dc3545;
    color: #dc3545;
    opacity: 0.7;
    font-size: 0.75rem;
    padding: 0.125rem 0.25rem;
}

.btn-outline-danger:hover {
    background-color: #dc3545;
    color: white;
    opacity: 1;
}
```

### 💾 **数据持久化**

#### **存储机制**
- 使用浏览器的`localStorage`进行本地存储
- 数据以JSON格式存储，键名为`llm_replay_model_history`
- 自动处理存储异常，确保功能稳定性

#### **数据结构**
```json
{
    "llm_replay_model_history": [
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-flash",
        "openai/gpt-4o",
        "anthropic/claude-haiku",
        "cohere/command-r-plus"
    ]
}
```

#### **容量限制**
- 最多保存10个历史记录（`MAX_HISTORY_ITEMS = 10`）
- 超出限制时自动删除最旧的记录
- 新记录总是添加到列表顶部

### 🔒 **错误处理**

#### **本地存储异常**
```javascript
try {
    localStorage.setItem(MODEL_HISTORY_KEY, JSON.stringify(history));
} catch (error) {
    console.error('Error saving model history:', error);
    // 静默失败，不影响用户体验
}
```

#### **JSON解析异常**
```javascript
try {
    const history = localStorage.getItem(MODEL_HISTORY_KEY);
    return history ? JSON.parse(history) : [];
} catch (error) {
    console.error('Error loading model history:', error);
    return []; // 返回空数组作为默认值
}
```

### 🚀 **性能优化**

#### **1. 事件防抖**
- 输入事件使用实时过滤，无需防抖
- 保存操作在失去焦点或按Enter时触发

#### **2. DOM操作优化**
- 下拉列表内容动态生成，避免不必要的DOM节点
- 使用事件委托减少事件监听器数量

#### **3. 内存管理**
- 历史记录数量限制在10个以内
- 及时清理不需要的事件监听器

### 📋 **使用示例**

#### **常见模型名称**
```
anthropic/claude-sonnet-4
anthropic/claude-haiku
google/gemini-2.5-flash
google/gemini-1.5-pro
openai/gpt-4o
openai/gpt-4o-mini
cohere/command-r-plus
meta-llama/llama-3.1-405b
```

#### **搜索过滤示例**
```
输入 "claude" → 显示:
- anthropic/claude-sonnet-4
- anthropic/claude-haiku

输入 "gpt" → 显示:
- openai/gpt-4o
- openai/gpt-4o-mini
```

### 🔄 **向后兼容性**

- ✅ 现有功能完全保持不变
- ✅ 输入框行为与之前一致
- ✅ 不影响现有的表单提交逻辑
- ✅ 历史记录功能为增强功能，不影响基础使用

### 🎯 **用户体验提升**

#### **便利性**
- 减少重复输入常用模型名称
- 提供快速选择历史记录的能力
- 支持模糊搜索快速定位

#### **可用性**
- 直观的下拉界面设计
- 清晰的删除操作反馈
- 响应式设计适配各种设备

#### **可维护性**
- 用户可以自主管理历史记录
- 删除不需要的历史项
- 自动限制历史记录数量

### 📈 **后续改进建议**

#### **1. 功能增强**
- 添加历史记录导入/导出功能
- 支持历史记录分类（按提供商分组）
- 添加使用频率统计

#### **2. 用户体验**
- 添加键盘导航支持（上下箭头选择）
- 支持历史记录排序（按时间/频率）
- 添加清空所有历史记录的功能

#### **3. 性能优化**
- 实现虚拟滚动处理大量历史记录
- 添加历史记录搜索高亮
- 优化移动端触摸体验

## 总结

Model Name历史记录功能为Test Execution页面提供了显著的用户体验提升：

1. ✅ **自动化**: 无需手动管理，自动保存和整理历史记录
2. ✅ **智能化**: 支持实时搜索过滤，快速定位所需模型
3. ✅ **可控性**: 用户可以删除不需要的历史记录
4. ✅ **持久化**: 使用本地存储，数据在浏览器会话间保持
5. ✅ **兼容性**: 不影响现有功能，纯增强型特性

这个功能特别适合经常使用不同LLM模型进行测试的用户，大大提高了工作效率和使用便利性。
