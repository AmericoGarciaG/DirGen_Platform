import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { WebSocketState } from '../../../../shared/models/dirgen.models';

@Component({
  selector: 'app-plan-widget',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatListModule],
  templateUrl: './plan-widget.component.html',
  styleUrls: ['./plan-widget.component.scss']
})
export class PlanWidgetComponent {
  @Input() webSocketState!: WebSocketState;
}