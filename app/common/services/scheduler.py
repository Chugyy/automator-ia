from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict, Any
import asyncio
from datetime import datetime
import uuid

from ...private.workflows.registry import workflow_registry
from ..engine import workflow_engine
from ..database.crud import *
from ..database.models import ScheduledJobModel

class WorkflowScheduler:
    """Scheduler pour l'exécution automatique des workflows"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Démarre le scheduler et programme tous les workflows actifs"""
        if self.is_running:
            return
        
        self.scheduler.start()
        self.is_running = True
        self._schedule_all_workflows()
    
    def stop(self):
        """Arrête le scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
    
    def _schedule_all_workflows(self):
        """Programme tous les workflows avec schedule et synchronise avec BDD"""
        workflows = workflow_registry.get_all_workflows()
        
        for name, workflow in workflows.items():
            config = workflow['config']
            
            # Vérifier que le workflow est actif et a un schedule
            if (config.get('active', True) and 
                'schedule' in config and 
                'schedule' in config.get('triggers', [])):
                
                # Vérifier que le workflow est actif en BDD aussi
                db_workflow = next((w for w in list_workflows() if w.name == name), None)
                if db_workflow and db_workflow.active:
                    self._schedule_workflow(name, config['schedule'], db_workflow.id)
    
    def _schedule_workflow(self, workflow_name: str, cron_expression: str, workflow_id: str):
        """Programme un workflow avec expression cron et sauvegarde en BDD"""
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            
            # Calculer prochaine exécution
            next_run = trigger.get_next_fire_time(None, datetime.now())
            
            # Ajouter job au scheduler APScheduler
            self.scheduler.add_job(
                self._execute_scheduled_workflow,
                trigger=trigger,
                args=[workflow_name, workflow_id],
                id=f"workflow_{workflow_name}",
                replace_existing=True
            )
            
            # Sauvegarder/Mettre à jour en BDD
            self._sync_job_to_db(workflow_id, cron_expression, next_run)
            
            print(f"✅ Job programmé: {workflow_name} - prochaine exécution: {next_run}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la programmation du workflow {workflow_name}: {e}")
    
    def _sync_job_to_db(self, workflow_id: str, cron_expression: str, next_run: datetime):
        """Synchronise un job avec la base de données"""
        try:
            # Chercher job existant
            existing_jobs = get_scheduled_jobs(active_only=False)
            existing_job = next((j for j in existing_jobs if j.workflow_id == workflow_id), None)
            
            if existing_job:
                # Mettre à jour job existant
                update_scheduled_job(existing_job.id, {
                    'cron_expression': cron_expression,
                    'active': True,
                    'next_run': next_run
                })
            else:
                # Créer nouveau job
                job = ScheduledJobModel(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow_id,
                    cron_expression=cron_expression,
                    active=True,
                    next_run=next_run
                )
                create_scheduled_job(job)
        except Exception as e:
            print(f"Erreur sync BDD job {workflow_id}: {e}")
    
    def _unschedule_workflow(self, workflow_name: str):
        """Annule la programmation d'un workflow"""
        job_id = f"workflow_{workflow_name}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            
        # Désactiver en BDD aussi
        db_workflow = next((w for w in list_workflows(active_only=False) if w.name == workflow_name), None)
        if db_workflow:
            existing_jobs = get_scheduled_jobs(active_only=False)
            existing_job = next((j for j in existing_jobs if j.workflow_id == db_workflow.id), None)
            if existing_job:
                update_scheduled_job(existing_job.id, {'active': False})
    
    def _execute_scheduled_workflow(self, workflow_name: str, workflow_id: str):
        """Exécute un workflow programmé après vérifications"""
        try:
            # 1. Vérifier que le workflow est toujours actif
            db_workflow = get_workflow(workflow_id)
            if not db_workflow or not db_workflow.active:
                print(f"⏸️ Workflow {workflow_name} désactivé - arrêt du job")
                self._unschedule_workflow(workflow_name)
                return
            
            # 2. Vérifier que tous les outils requis sont actifs
            if not self._are_tools_active(db_workflow.tools_required):
                print(f"⏸️ Outils requis inactifs pour {workflow_name} - saut de cette exécution")
                return
            
            # 3. Mettre à jour last_run en BDD
            self._update_job_last_run(workflow_id)
            
            # 4. Exécuter le workflow
            print(f"🚀 Exécution programmée: {workflow_name}")
            result = workflow_engine.execute_workflow(
                workflow_name, 
                data={}, 
                trigger_type="schedule"
            )
            
            # 5. Calculer et mettre à jour next_run
            self._update_job_next_run(workflow_id, workflow_name)
            
            print(f"✅ Exécution programmée terminée: {workflow_name} - Status: {result.get('status', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution programmée de {workflow_name}: {e}")
    
    def reload_schedules(self):
        """Recharge tous les schedules après changement"""
        if not self.is_running:
            return
        
        self.scheduler.remove_all_jobs()
        self._schedule_all_workflows()
    
    def _are_tools_active(self, tools_required: list) -> bool:
        """Vérifie que tous les outils requis sont actifs"""
        if not tools_required:
            return True
            
        for tool_name in tools_required:
            tool = get_tool_by_name(tool_name, active_only=True)
            if not tool:
                return False
        return True
    
    def _update_job_last_run(self, workflow_id: str):
        """Met à jour last_run du job"""
        try:
            existing_jobs = get_scheduled_jobs(active_only=False)
            existing_job = next((j for j in existing_jobs if j.workflow_id == workflow_id), None)
            if existing_job:
                update_scheduled_job(existing_job.id, {'last_run': datetime.now()})
        except Exception as e:
            print(f"Erreur MAJ last_run {workflow_id}: {e}")
    
    def _update_job_next_run(self, workflow_id: str, workflow_name: str):
        """Met à jour next_run du job"""
        try:
            job_id = f"workflow_{workflow_name}"
            apscheduler_job = self.scheduler.get_job(job_id)
            if apscheduler_job:
                next_run = apscheduler_job.next_run_time
                existing_jobs = get_scheduled_jobs(active_only=False)
                existing_job = next((j for j in existing_jobs if j.workflow_id == workflow_id), None)
                if existing_job:
                    update_scheduled_job(existing_job.id, {'next_run': next_run})
        except Exception as e:
            print(f"Erreur MAJ next_run {workflow_id}: {e}")

    def update_workflow_schedule(self, workflow_name: str, active: bool):
        """Met à jour le schedule d'un workflow spécifique"""
        if active:
            workflow = workflow_registry.get_workflow(workflow_name)
            if workflow and 'schedule' in workflow['config']:
                db_workflow = next((w for w in list_workflows() if w.name == workflow_name), None)
                if db_workflow:
                    self._schedule_workflow(workflow_name, workflow['config']['schedule'], db_workflow.id)
        else:
            self._unschedule_workflow(workflow_name)
    
    def get_scheduled_jobs_info(self) -> list:
        """Retourne les informations des jobs programmés"""
        jobs_info = []
        scheduled_jobs = get_scheduled_jobs(active_only=True)
        
        for job in scheduled_jobs:
            workflow = get_workflow(job.workflow_id)
            if workflow:
                jobs_info.append({
                    'id': job.id,
                    'workflow_name': workflow.name,
                    'workflow_display_name': workflow.display_name,
                    'cron_expression': job.cron_expression,
                    'active': job.active,
                    'next_run': job.next_run,
                    'last_run': job.last_run,
                    'workflow_active': workflow.active
                })
        
        return jobs_info

workflow_scheduler = WorkflowScheduler()