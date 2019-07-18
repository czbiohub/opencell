
import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button } from "@blueprintjs/core";
import classNames from 'classnames';


class ColumnControls extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }


    render() {
        return (
            <div className="pr3">
                {this.props.columnGroups.map((group, index) => (
                    <div key={index} className="pb3">
                        <div className="b">{group.name}</div>
                        <ColumnGroupButtons group={group} {...this.props}/>
                    </div>
                ))}
            </div>
        );
    }
}


class ColumnGroupButtons extends Component {
    constructor (props) {
        super(props);
    }

    render() {
        return this.props.group.ids.map(id => {
            const def = this.props.columnDefs.filter(def => def.id===id).pop();
            if (!def) return <div key={id} className="black-30">{id}</div>;
            return (
                <SimpleButton 
                    active={this.props.selectedColumns.includes(id)} 
                    onClick={d => this.props.toggleColumn(id)} 
                    text={def.Header}
                    key={id}/>
            );
        });
    }
}


function SimpleButton(props) {
    const className = classNames("pr2 simple-button", {'simple-button-active': props.active});
    return <div className={className} onClick={props.onClick}>{props.text}</div>;
}


export default ColumnControls;