// Dashboard API Management
class DashboardAPI {
    constructor() {
        this.baseURL = '/dashboard/api';
    }

    async fetchStats() {
        const response = await fetch(`${this.baseURL}/stats`);
        return response.json();
    }

    async fetchEnv() {
        const response = await fetch(`${this.baseURL}/env`);
        return response.json();
    }

    async toggleWorkflow(workflowName) {
        const response = await fetch(`${this.baseURL}/workflows/${workflowName}/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        return response.json();
    }

    async getWorkflowLogs(workflowName) {
        const response = await fetch(`${this.baseURL}/workflows/${workflowName}/logs`);
        return response.json();
    }

    async toggleTool(toolName) {
        const response = await fetch(`${this.baseURL}/tools/${toolName}/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        return response.json();
    }

    async createProfile(toolName, profileName, config) {
        const response = await fetch(`${this.baseURL}/tools/${toolName}/profiles/${profileName}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({config})
        });
        return response.json();
    }

    async updateProfile(toolName, profileName, config) {
        const response = await fetch(`${this.baseURL}/tools/${toolName}/profiles/${profileName}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({config})
        });
        return response.json();
    }

    async getToolConfigSchema(toolName) {
        const response = await fetch(`${this.baseURL}/tools/${toolName}/config-schema`);
        return response.json();
    }

    async deleteProfile(toolName, profileName) {
        const response = await fetch(`${this.baseURL}/tools/${toolName}/profiles/${profileName}`, {
            method: 'DELETE'
        });
        return response.json();
    }

    async executeWorkflow(workflowName) {
        const response = await fetch('/api/workflows/execute/' + workflowName, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });
        return response.json();
    }

    async getWorkflowConfig(workflowName) {
        const response = await fetch(`${this.baseURL}/workflows/${workflowName}/config`);
        return response.json();
    }

    async updateWorkflowToolProfiles(workflowName, toolProfiles) {
        const response = await fetch(`${this.baseURL}/workflows/${workflowName}/tool-profiles`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tool_profiles: toolProfiles })
        });
        return response.json();
    }
}

// Profile Modal Management
class ProfileModal {
    constructor() {
        this.modal = null;
        this.currentTool = null;
        this.currentProfile = null;
        this.isEdit = false;
        this.init();
    }

    init() {
        // Create modal HTML
        const modalHTML = `
            <div id="profile-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 id="modal-title">Tool Profiles</h2>
                        <button class="modal-close" onclick="profileModal.close()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div id="profiles-list"></div>
                        <div id="profile-form" style="display: none;">
                            <h3 id="form-title">Add Profile</h3>
                            <form onsubmit="profileModal.saveProfile(event)">
                                <input type="text" id="profile-name" placeholder="Profile name" required>
                                <div id="config-fields"></div>
                                <div class="form-actions">
                                    <button type="submit" class="btn-primary">Save</button>
                                    <button type="button" class="btn-secondary" onclick="profileModal.hideForm()">Cancel</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('profile-modal');
    }

    open(toolName, toolData) {
        this.currentTool = toolName;
        this.toolData = toolData;
        document.getElementById('modal-title').textContent = `${toolData.display_name} - Profiles`;
        this.renderProfiles();
        this.modal.style.display = 'flex';
    }

    close() {
        this.modal.style.display = 'none';
        this.hideForm();
    }

    renderProfiles() {
        const container = document.getElementById('profiles-list');
        const profiles = this.toolData.profiles || [];
        
        container.innerHTML = `
            <div class="profiles-header">
                <h3>Profils Existants (${profiles.length})</h3>
                <button class="btn-primary" onclick="profileModal.showForm()">Nouveau Profil</button>
            </div>
            <div class="profiles-grid">
                ${profiles.length === 0 ? 
                    '<div class="no-profiles">Aucun profil configuré</div>' :
                    profiles.map(profile => {
                        const configEntries = Object.entries(profile.config || {});
                        const configCount = configEntries.length;
                        
                        return `
                        <div class="profile-card">
                            <div class="profile-card-header">
                                <h4>${profile.name}</h4>
                                <span class="profile-badge">${configCount} param${configCount > 1 ? 's' : ''}</span>
                            </div>
                            <div class="profile-config">
                                ${configEntries.map(([key, value]) => {
                                    const isSecret = key.toLowerCase().includes('token') || 
                                                   key.toLowerCase().includes('key') || 
                                                   key.toLowerCase().includes('password') ||
                                                   key.toLowerCase().includes('secret');
                                    
                                    let displayValue;
                                    let tooltip = '';
                                    
                                    if (isSecret) {
                                        displayValue = '••••••••';
                                        tooltip = 'Valeur masquée pour sécurité';
                                    } else if (value.length > 25) {
                                        displayValue = value.substring(0, 25) + '...';
                                        tooltip = value;
                                    } else {
                                        displayValue = value;
                                        tooltip = value;
                                    }
                                    
                                    return `<div class="config-item">
                                        <div class="config-key">${key.replace(/_/g, ' ')}</div>
                                        <div class="config-value ${isSecret ? 'secret' : ''}" title="${tooltip}">
                                            ${displayValue}
                                        </div>
                                    </div>`;
                                }).join('')}
                            </div>
                            <div class="profile-actions">
                                <button class="btn-sm" onclick="profileModal.editProfile('${profile.name}', ${JSON.stringify(profile.config).replace(/"/g, '&quot;')})">Modifier</button>
                                <button class="btn-sm btn-danger" onclick="profileModal.deleteProfile('${profile.name}')">Supprimer</button>
                            </div>
                        </div>`;
                    }).join('')
                }
            </div>
        `;
    }

    async showForm(isEdit = false) {
        this.isEdit = isEdit;
        document.getElementById('form-title').textContent = isEdit ? 'Edit Profile' : 'Add Profile';
        document.getElementById('profile-form').style.display = 'block';
        await this.generateConfigFields();
    }

    hideForm() {
        document.getElementById('profile-form').style.display = 'none';
        document.getElementById('profile-name').value = '';
        this.currentProfile = null;
        this.isEdit = false;
    }

    async editProfile(profileName, config) {
        this.currentProfile = profileName;
        await this.showForm(true);
        document.getElementById('profile-name').value = profileName;
        document.getElementById('profile-name').disabled = true;
        
        // Fill config fields after generation
        setTimeout(() => {
            Object.entries(config || {}).forEach(([key, value]) => {
                const field = document.getElementById(`config-${key}`);
                if (field) field.value = value;
            });
        }, 100);
    }

    async generateConfigFields() {
        const container = document.getElementById('config-fields');
        const toolName = this.currentTool;
        
        try {
            const schema = await api.getToolConfigSchema(toolName);
            let fields = '';
            
            // Generate required fields
            for (const param of schema.required_params || []) {
                const isToken = param.toLowerCase().includes('token') || param.toLowerCase().includes('key');
                const inputType = isToken ? 'password' : 'text';
                fields += `<div class="config-field">
                    <label>${param.charAt(0).toUpperCase() + param.slice(1)}:</label>
                    <input type="${inputType}" id="config-${param}" placeholder="Required ${param}" required>
                </div>`;
            }
            
            // Generate optional fields
            for (const [param, defaultValue] of Object.entries(schema.optional_params || {})) {
                const isToken = param.toLowerCase().includes('token') || param.toLowerCase().includes('key');
                const inputType = isToken ? 'password' : 'text';
                const placeholder = defaultValue ? `Optional (default: ${defaultValue})` : `Optional ${param}`;
                fields += `<div class="config-field">
                    <label>${param.charAt(0).toUpperCase() + param.slice(1)}:</label>
                    <input type="${inputType}" id="config-${param}" placeholder="${placeholder}">
                </div>`;
            }
            
            if (!fields) {
                fields = '<div class="no-config">This tool requires no configuration.</div>';
            }
            
            container.innerHTML = fields;
        } catch (error) {
            console.error('Failed to load config schema:', error);
            container.innerHTML = '<div class="error">Failed to load configuration schema</div>';
        }
    }

    async saveProfile(event) {
        event.preventDefault();
        
        const profileName = document.getElementById('profile-name').value;
        const config = {};
        
        // Collect config from form
        document.querySelectorAll('#config-fields input').forEach(input => {
            const key = input.id.replace('config-', '');
            if (input.value.trim()) {
                config[key] = input.value.trim();
            }
        });
        
        try {
            let result;
            if (this.isEdit) {
                result = await api.updateProfile(this.currentTool, profileName, config);
            } else {
                result = await api.createProfile(this.currentTool, profileName, config);
            }
            
            if (result.status === 'success') {
                this.hideForm();
                // Refresh tool data
                const stats = await api.fetchStats();
                this.toolData = stats.tools.find(t => t.name === this.currentTool);
                this.renderProfiles();
                dashboard.loadDashboard(); // Refresh main dashboard
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }

    async deleteProfile(profileName) {
        if (!confirm(`Delete profile "${profileName}"?`)) return;
        
        try {
            const result = await api.deleteProfile(this.currentTool, profileName);
            if (result.status === 'success') {
                const stats = await api.fetchStats();
                this.toolData = stats.tools.find(t => t.name === this.currentTool);
                this.renderProfiles();
                dashboard.loadDashboard();
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }
}

// Workflow Configuration Modal Management
class WorkflowConfigModal {
    constructor() {
        this.modal = null;
        this.api = new DashboardAPI();
    }

    async open(workflowName) {
        if (this.modal) {
            this.modal.remove();
        }

        try {
            const config = await this.api.getWorkflowConfig(workflowName);
            this.render(config);
        } catch (error) {
            console.error('Failed to load workflow config:', error);
            alert('Failed to load workflow configuration');
        }
    }

    render(config) {
        const { workflow, tools } = config;
        
        this.modal = document.createElement('div');
        this.modal.className = 'modal-overlay';
        this.modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Configure Tools - ${workflow.display_name || workflow.name}</h3>
                    <button onclick="workflowConfigModal.close()" class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <p class="modal-description">${workflow.description || 'Configure tool profiles for this workflow'}</p>
                    <div class="tools-config">
                        ${tools.map(tool => this.renderToolConfig(tool)).join('')}
                    </div>
                </div>
                <div class="modal-footer">
                    <button onclick="workflowConfigModal.close()" class="btn-secondary">Cancel</button>
                    <button onclick="workflowConfigModal.save('${workflow.name}')" class="btn-primary">Save Configuration</button>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);
    }

    renderToolConfig(tool) {
        const profiles = tool.profiles || [];
        const selectedProfile = tool.selected_profile || 'DEFAULT';
        
        return `
            <div class="tool-config-item">
                <div class="tool-config-header">
                    <img src="/dashboard/api/tools/${tool.name}/logo" alt="${tool.display_name}" class="tool-logo-small" onerror="this.style.display='none'">
                    <div class="tool-info">
                        <h4>${tool.display_name}</h4>
                        <p>Select profile for this tool</p>
                    </div>
                </div>
                <div class="profile-selector">
                    <select data-tool="${tool.name}" class="profile-select">
                        <option value="DEFAULT" ${selectedProfile === 'DEFAULT' ? 'selected' : ''}>DEFAULT</option>
                        ${profiles.map(profile => 
                            `<option value="${profile.name}" ${selectedProfile === profile.name ? 'selected' : ''}>${profile.name}</option>`
                        ).join('')}
                    </select>
                </div>
            </div>
        `;
    }

    async save(workflowName) {
        const selects = this.modal.querySelectorAll('.profile-select');
        const toolProfiles = {};
        
        selects.forEach(select => {
            const toolName = select.dataset.tool;
            const profile = select.value;
            if (profile !== 'DEFAULT') {
                toolProfiles[toolName] = profile;
            }
        });

        try {
            const result = await this.api.updateWorkflowToolProfiles(workflowName, toolProfiles);
            if (result.status === 'success') {
                this.close();
                // Recharger les données du dashboard
                dashboard.loadDashboard();
                alert('Tool profiles updated successfully!');
            } else {
                alert('Failed to update tool profiles');
            }
        } catch (error) {
            console.error('Failed to save:', error);
            alert('Failed to save configuration');
        }
    }

    close() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
        }
    }
}

// Main Dashboard Class
class Dashboard {
    constructor() {
        this.api = new DashboardAPI();
    }

    async loadDashboard() {
        try {
            const [data, envData] = await Promise.all([
                this.api.fetchStats(),
                this.api.fetchEnv().catch(() => ({ variables: {}, count: 0 }))
            ]);
            
            window.ENV_VARS = envData.variables || {};
            
            this.updateStats(data.stats, data.workflows.length, data.interfaces.length);
            this.renderTools(data.tools);
            this.renderWorkflows(data.workflows);
            this.renderInterfaces(data.interfaces);
            
        } catch (error) {
            console.error('Loading error:', error);
            document.getElementById('tools').innerHTML = '<div class="loading">Loading error</div>';
        }
    }

    updateStats(stats, workflowCount, interfaceCount) {
        document.getElementById('active-workflows').textContent = workflowCount;
    }

    renderTools(tools) {
        const container = document.getElementById('tools');
        
        if (!tools || tools.length === 0) {
            container.innerHTML = '<div class="loading">Aucun outil disponible</div>';
            return;
        }
        
        container.innerHTML = tools.map(tool => `
            <aside class="tool-card ${tool.active ? '' : 'inactive'}">
                <div class="tool-header">
                    <img src="/dashboard/api/tools/${tool.name}/logo" alt="${tool.display_name}" class="tool-logo" onerror="this.style.display='none'">
                    <div class="tool-info">
                        <h3>${tool.display_name}</h3>
                        <p>${tool.profiles.length} profil(s) configuré(s)</p>
                    </div>
                    <div class="tool-toggle">
                        <label class="switch">
                            <input type="checkbox" ${tool.active ? 'checked' : ''} 
                                   onchange="dashboard.toggleTool('${tool.name}', this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="tool-status">
                    <span class="status ${tool.active ? 'active' : 'inactive'}">${tool.active ? 'Actif' : 'Inactif'}</span>
                </div>
                <div class="tool-actions">
                    <button onclick="profileModal.open('${tool.name}', ${JSON.stringify(tool).replace(/"/g, '&quot;')})" class="btn-primary">Gérer les Profils</button>
                </div>
            </aside>
        `).join('');
    }

    renderWorkflows(workflows) {
        const container = document.getElementById('workflows');
        
        if (workflows.length === 0) {
            container.innerHTML = '<div class="loading">Aucun workflow disponible</div>';
            return;
        }
        
        container.innerHTML = workflows.map(workflow => `
            <aside class="${workflow.active ? '' : 'inactive'}">
                <div class="workflow-header">
                    <div>
                        <h3>${workflow.display_name || workflow.name}</h3>
                        <p>${workflow.description || 'Aucune description'}</p>
                    </div>
                    <div class="workflow-toggle">
                        <label class="switch">
                            <input type="checkbox" ${workflow.active ? 'checked' : ''} 
                                   onchange="dashboard.toggleWorkflow('${workflow.name}', this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="workflow-meta">
                    <span class="status ${workflow.active ? 'active' : 'inactive'}">${workflow.active ? 'Actif' : 'Inactif'}</span>
                    <span class="category">${workflow.category || 'Général'}</span>
                </div>
                <div class="workflow-actions">
                    <a href="#" onclick="dashboard.runWorkflow('${workflow.name}'); return false;" class="btn-primary" ${workflow.active ? '' : 'style="opacity:0.5;pointer-events:none;"'}>Exécuter</a>
                    <a href="#" onclick="dashboard.showLogs('${workflow.name}'); return false;" class="btn-secondary">Logs</a>
                    <a href="#" onclick="workflowConfigModal.open('${workflow.name}'); return false;" class="btn-secondary">Configurer</a>
                </div>
            </aside>
        `).join('');
    }

    renderInterfaces(interfaces) {
        const container = document.getElementById('interfaces');
        
        if (!interfaces || interfaces.length === 0) {
            container.innerHTML = '<div class="loading">Aucune interface disponible</div>';
            return;
        }
        
        // Séparer par type
        const commonInterfaces = interfaces.filter(i => i.type === 'common');
        const privateInterfaces = interfaces.filter(i => i.type === 'private');
        
        let html = '';
        
        if (commonInterfaces.length > 0) {
            html += `<div class="interfaces-section">
                <h3 class="section-title">🛠️ Admin / Général</h3>
                ${commonInterfaces.map(interfaceItem => `
                    <aside class="interface-common">
                        <a href="${interfaceItem.route}" class="interface-link">
                            <h4>${interfaceItem.display_name}</h4>
                            <p>${interfaceItem.description}</p>
                        </a>
                    </aside>
                `).join('')}
            </div>`;
        }
        
        if (privateInterfaces.length > 0) {
            html += `<div class="interfaces-section">
                <h3 class="section-title">👤 Utilisateur</h3>
                ${privateInterfaces.map(interfaceItem => `
                    <aside class="interface-private">
                        <a href="${interfaceItem.route}" class="interface-link">
                            <h4>${interfaceItem.display_name}</h4>
                            <p>${interfaceItem.description}</p>
                        </a>
                    </aside>
                `).join('')}
            </div>`;
        }
        
        container.innerHTML = html;
    }

    async toggleTool(toolName, isChecked) {
        try {
            const result = await this.api.toggleTool(toolName);
            if (result.status === 'success') {
                this.loadDashboard();
            } else {
                alert('Error: ' + result.message);
                this.loadDashboard();
            }
        } catch (error) {
            alert('Erreur lors du basculement de l\'outil: ' + error);
            this.loadDashboard();
        }
    }

    async toggleWorkflow(workflowName, isChecked) {
        try {
            const result = await this.api.toggleWorkflow(workflowName);
            if (result.status === 'success') {
                this.loadDashboard();
            } else {
                alert('Error: ' + result.message);
                this.loadDashboard();
            }
        } catch (error) {
            alert('Erreur lors du basculement du workflow: ' + error);
            this.loadDashboard();
        }
    }

    async runWorkflow(workflowName) {
        if(!confirm('Exécuter le workflow ' + workflowName + ' ?')) return;
        
        try {
            const result = await this.api.executeWorkflow(workflowName);
            alert('Résultat: ' + result.status + ' - ' + result.message);
            this.loadDashboard();
        } catch (error) {
            alert('Erreur: ' + error);
        }
    }

    async showLogs(workflowName) {
        try {
            const data = await this.api.getWorkflowLogs(workflowName);
            
            const logsWindow = window.open('', '_blank');
            const logsHtml = `
                <html>
                <head><title>Logs - ${workflowName}</title>
                <style>
                    body { font-family: monospace; padding: 20px; background: #f5f5f5; }
                    .log-entry { background: white; margin: 10px 0; padding: 10px; border-left: 3px solid #007bff; }
                    .error { border-left-color: #dc3545; }
                    .success { border-left-color: #28a745; }
                    .timestamp { color: #666; font-size: 0.9em; }
                </style>
                </head>
                <body>
                    <h1>Logs pour ${workflowName}</h1>
                    ${data.logs.length === 0 ? 
                        '<p>Aucun log disponible</p>' : 
                        data.logs.map(log => 
                            '<div class="log-entry ' + (log.level || '') + '">' +
                                '<div class="timestamp">' + (log.timestamp || 'Pas de timestamp') + '</div>' +
                                '<div>' + (log.message || JSON.stringify(log)) + '</div>' +
                            '</div>'
                        ).join('')
                    }
                    <script>setTimeout(() => window.close(), 30000);<\/script>
                </body>
                </html>
            `;
            logsWindow.document.write(logsHtml);
            logsWindow.document.close();
            
        } catch (error) {
            alert('Erreur lors du chargement des logs: ' + error);
        }
    }
}

// Global instances
const api = new DashboardAPI();
const profileModal = new ProfileModal();
const workflowConfigModal = new WorkflowConfigModal();
const dashboard = new Dashboard();

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    dashboard.loadDashboard();
});
